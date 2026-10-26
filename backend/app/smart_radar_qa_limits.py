"""QA controls built on existing BAWASLU and OpenAI configuration.

No new Render variables are required. The QA lab is NEVER started by the
automatic campaign worker. Requests are explicitly triggered by an authorized
national administrator and persisted in the QA-only assessment table.
QA is not subject to the election campaign's per-day request quota.
The per-click and lifetime guardrails remain in force to limit accidental spend.
Campaign workers continue to use their existing settings independently.
"""
import os
from fastapi import HTTPException
from sqlalchemy import text

_DEFAULT_MODEL="gpt-4o-mini"
_DEFAULT_URL="https://api.openai.com/v1"
_MAX_QA_RUN=3
_MAX_QA_LIFETIME=200

def _safe_limit(name, default, maximum):
    raw=os.getenv(name)
    if raw is None or not raw.strip():
        return min(default,maximum)
    try:
        return max(0,min(maximum,int(raw.strip())))
    except (ValueError,TypeError):
        # Invalid explicit limits must fail closed, never become unlimited.
        return 0

def qa_config():
    model=(os.getenv("OPENAI_MODEL","").strip()
           or os.getenv("BAWASLU_RELEVANCE_MODEL","").strip()
           or _DEFAULT_MODEL)
    key=os.getenv("OPENAI_API_KEY","").strip()
    base=(os.getenv("OPENAI_BASE_URL","").strip() or _DEFAULT_URL).rstrip("/")
    max_run=_safe_limit("BAWASLU_AI_ASSESSMENTS_PER_RUN",_MAX_QA_RUN,_MAX_QA_RUN)
    lifetime=_safe_limit("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN",_MAX_QA_LIFETIME,_MAX_QA_LIFETIME)
    return {"model":model,"key":key,"base_url":base,"max_run":max_run,
            "daily":None,"lifetime":lifetime,
            "model_source":("OPENAI_MODEL" if os.getenv("OPENAI_MODEL","").strip() else
                            "BAWASLU_RELEVANCE_MODEL" if os.getenv("BAWASLU_RELEVANCE_MODEL","").strip() else
                            "built-in gpt-4o-mini default")}

def qa_budget(db):
    # Successful predictions are counted from the assessment table. Failed or
    # in-flight prompt-tuning calls have no saved prediction yet, but may still
    # consume provider tokens. Include them to prevent unbounded retries.
    row=db.execute(text("""SELECT
        (SELECT count(*) FROM pilot_smart_radar.qa_ai_assessments)
          + (SELECT count(*) FROM pilot_smart_radar.qa_prompt_attempts
             WHERE attempt_status IN ('failed','started')) AS used_lifetime,
        (SELECT count(*) FROM pilot_smart_radar.qa_ai_assessments
             WHERE processed_at >= CURRENT_DATE)
          + (SELECT count(*) FROM pilot_smart_radar.qa_prompt_attempts
             WHERE attempted_at >= CURRENT_DATE
               AND attempt_status IN ('failed','started')) AS used_today
        """)).mappings().first()
    return {"used_today":int(row["used_today"] or 0),
            "used_lifetime":int(row["used_lifetime"] or 0)}

def qa_readiness(db):
    cfg=qa_config()
    used=qa_budget(db)
    return {**cfg,**used,
        "daily_remaining":None,
        "lifetime_remaining":max(0,cfg["lifetime"]-used["used_lifetime"]),
        "ready":bool(cfg["model"] and cfg["key"] and cfg["max_run"]>0
                     and used["used_lifetime"]<cfg["lifetime"])}

def ensure_qa_batch(db,requested):
    cfg=qa_readiness(db)
    if not cfg["key"]:
        raise HTTPException(409,"OPENAI_API_KEY is not configured on the staging backend")
    if cfg["max_run"]<=0 or cfg["lifetime"]<=0:
        raise HTTPException(409,"Existing BAWASLU AI request limits are zero or invalid")
    if requested>cfg["max_run"]:
        raise HTTPException(409,"QA batch exceeds BAWASLU_AI_ASSESSMENTS_PER_RUN")
    if cfg["used_lifetime"]+requested>cfg["lifetime"]:
        raise HTTPException(429,"Lifetime QA request cap reached")
    return cfg
