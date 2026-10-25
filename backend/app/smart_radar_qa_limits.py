"""QA controls built on existing BAWASLU and OpenAI configuration.

No new Render variables are required. The QA lab is NEVER started by the
automatic campaign worker. Requests are explicitly triggered by an authorized
national administrator and persisted in the QA-only assessment table.
Existing per-campaign caps are used as additional upper bounds; QA has its
own counters and does not claim to reserve campaign-worker budget.
"""
import os
from fastapi import HTTPException
from sqlalchemy import text

_DEFAULT_MODEL="gpt-4o-mini"
_DEFAULT_URL="https://api.openai.com/v1"
_MAX_QA_RUN=3
_MAX_QA_DAILY=30
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
    daily=_safe_limit("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN",_MAX_QA_DAILY,_MAX_QA_DAILY)
    lifetime=_safe_limit("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN",_MAX_QA_LIFETIME,_MAX_QA_LIFETIME)
    return {"model":model,"key":key,"base_url":base,"max_run":max_run,
            "daily":daily,"lifetime":lifetime,
            "model_source":("OPENAI_MODEL" if os.getenv("OPENAI_MODEL","").strip() else
                            "BAWASLU_RELEVANCE_MODEL" if os.getenv("BAWASLU_RELEVANCE_MODEL","").strip() else
                            "built-in gpt-4o-mini default")}

def qa_budget(db):
    row=db.execute(text("""SELECT
        count(*)::int AS used_lifetime,
        count(*) FILTER (WHERE processed_at >= CURRENT_DATE)::int AS used_today
        FROM pilot_smart_radar.qa_ai_assessments""")).mappings().first()
    return {"used_today":int(row["used_today"] or 0),
            "used_lifetime":int(row["used_lifetime"] or 0)}

def qa_readiness(db):
    cfg=qa_config()
    used=qa_budget(db)
    return {**cfg,**used,
        "daily_remaining":max(0,cfg["daily"]-used["used_today"]),
        "lifetime_remaining":max(0,cfg["lifetime"]-used["used_lifetime"]),
        "ready":bool(cfg["model"] and cfg["key"] and cfg["max_run"]>0
                     and used["used_today"]<cfg["daily"]
                     and used["used_lifetime"]<cfg["lifetime"])}

def ensure_qa_batch(db,requested):
    cfg=qa_readiness(db)
    if not cfg["key"]:
        raise HTTPException(409,"OPENAI_API_KEY is not configured on the staging backend")
    if cfg["max_run"]<=0 or cfg["daily"]<=0 or cfg["lifetime"]<=0:
        raise HTTPException(409,"Existing BAWASLU AI request limits are zero or invalid")
    if requested>cfg["max_run"]:
        raise HTTPException(409,"QA batch exceeds BAWASLU_AI_ASSESSMENTS_PER_RUN")
    if cfg["used_today"]+requested>cfg["daily"]:
        raise HTTPException(429,"Daily QA request cap reached")
    if cfg["used_lifetime"]+requested>cfg["lifetime"]:
        raise HTTPException(429,"Lifetime QA request cap reached")
    return cfg
