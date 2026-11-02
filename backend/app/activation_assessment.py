"""Activation and Assess All orchestration using durable saved jobs.

The SocialCrawl collection is paid independently. Every AI request is reserved
and metered by the existing full relevance worker; this module does not call
OpenAI itself or treat preliminary PRISM labels as completed full assessments.
"""
import json
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .access import allowed, has
from .models import (MonitoringCampaign, CampaignRun, CampaignEvidence,
                     SocialListeningRun, EvidenceAssessment, AIAssessmentJob)
from .sentiment_processing import relevance_is_assessed


def needs_full_assessment(record):
    if not record:
        return True
    model = str(record.model_version or "").upper()
    if model in ("PRISM_PENDING_OPENAI", "PRISM_OPENAI_TOPIC_CLASSIFIER"):
        return True
    return not relevance_is_assessed(record)


def _latest(db, campaign_id, result_id):
    return (db.query(EvidenceAssessment)
            .filter_by(campaign_id=int(campaign_id), result_id=int(result_id))
            .order_by(__import__('sqlalchemy').case(
                (EvidenceAssessment.model_version.in_(['PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER']),1),
                else_=0).asc(),EvidenceAssessment.assessment_version.desc(),
                      EvidenceAssessment.id.desc()).first())


def remaining_budget(db, campaign_id):
    """Match the existing automatic reservation worker's hard ceilings."""
    from .models import AIBudgetReservation
    def cap(name, maximum):
        try:
            return max(0, min(maximum, int(os.getenv(name, "0"))))
        except (TypeError, ValueError):
            return 0
    daily = cap("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN", 100)
    lifetime = cap("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN", 500)
    per_run = cap("BAWASLU_AI_ASSESSMENTS_PER_RUN", 25)
    rows = db.query(AIBudgetReservation).filter(
        AIBudgetReservation.campaign_id == int(campaign_id)).all()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    reserved = {r.budget_period: int(r.reserved_requests or 0) for r in rows}
    return {"available": max(0, min(daily - reserved.get(today, 0),
                                      lifetime - reserved.get("lifetime", 0))),
            "daily_limit": daily, "lifetime_limit": lifetime,
            "per_run": per_run, "provider_ready": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "database_ready": db.bind.dialect.name == "postgresql"}


def _run(db, principal, campaign_id, run_id):
    c = db.get(MonitoringCampaign, int(campaign_id))
    if not c or not allowed(principal, c):
        raise PermissionError("Campaign unavailable")
    run = (db.query(SocialListeningRun).join(
        CampaignRun, CampaignRun.social_listening_run_id == SocialListeningRun.id)
        .filter(CampaignRun.campaign_id == c.id,
                SocialListeningRun.id == int(run_id),
                SocialListeningRun.provider.in_(("SOCIALCRAWL_PRISM", "AI_ASSESS_ALL")))
        .first())
    if not run:
        raise ValueError("Assessment run not found in this campaign")
    return c, run


def stale_processing_claim(job, at=None):
    """Detect an interrupted worker without retrying or modifying a paid request."""
    if not job or job.state != "PROCESSING" or not job.updated_at:
        return False
    return job.updated_at < ((at or datetime.utcnow()) - timedelta(minutes=10))


def status(db, principal, campaign_id, run_id):
    c, run = _run(db, principal, campaign_id, run_id)
    try:
        meta = json.loads(run.query_json or "{}")
    except (ValueError, TypeError):
        meta = {}
    ids = [int(x) for x in meta.get("assessment_result_ids", [])[:500]
           if str(x).isdigit()]
    if not ids:
        stage = ("FAILED" if run.status == "FAILED" else
                 "COLLECTING" if run.status in ("QUEUED", "RUNNING") else
                 "NO_NEW_POSTS")
        return {"run_id":run.id,"status":run.status,"stage":stage,
                "posts_saved":int(run.result_count or 0),"total":0,"completed":0,
                "queued":0,"processing":0,"failed":0,"blocked":0,
                "progress_percent":0,"credits_used":int(run.credits_used or 0),
                "error":run.error_text or "", "budget":remaining_budget(db,c.id)}
    assessments = {}
    for row in (db.query(EvidenceAssessment).filter(
            EvidenceAssessment.campaign_id == c.id,
            EvidenceAssessment.result_id.in_(ids))
            .order_by(EvidenceAssessment.assessment_version.desc(),
                      EvidenceAssessment.id.desc()).all()):
        assessments.setdefault(row.result_id, row)
    jobs = {j.result_id:j for j in db.query(AIAssessmentJob).filter(
        AIAssessmentJob.campaign_id == c.id, AIAssessmentJob.result_id.in_(ids)).all()}
    totals = {"completed":0,"queued":0,"processing":0,"failed":0,"blocked":0,"stalled":0}
    # Jobs older than the automatic quarantine window are not proof of a live
    # provider request. Keep them untouched until an explicitly authorized resume.

    for rid in ids:
        previous = assessments.get(rid)
        if not needs_full_assessment(previous):
            totals["completed"] += 1
        else:
            job = jobs.get(rid)
            if job and job.state == "PROCESSING":
                if stale_processing_claim(job):
                    totals["stalled"] += 1
                else:
                    totals["processing"] += 1
            elif job and job.state == "PENDING":
                totals["queued"] += 1
            elif job and job.state in ("FAILED","COMPLETED"):
                totals["failed"] += 1
            else:
                totals["blocked"] += 1
    if run.status == "FAILED":
        stage = "FAILED"
    elif run.status in ("QUEUED", "RUNNING") and not meta.get("assessment_result_ids"):
        stage = "COLLECTING"
    elif totals["completed"] == len(ids):
        stage = "COMPLETED"
    elif totals["stalled"]:
        stage = "NEEDS_ATTENTION"
    elif totals["queued"] or totals["processing"]:
        budget = remaining_budget(db, c.id)
        stage = ("NEEDS_ATTENTION" if totals["queued"] and not totals["processing"]
                 and (meta.get("assessment_worker_complete") or not budget["provider_ready"] or not budget["database_ready"]
                      or budget["available"] == 0) else "ASSESSING")
    elif totals["failed"] or totals["blocked"]:
        stage = "NEEDS_ATTENTION"
    else:
        stage = "ASSESSING"
    budget = remaining_budget(db,c.id)
    reason = ("A worker has not updated a processing request in over 10 minutes. "
              "The uncertain request will not be charged again automatically." if totals["stalled"]
              else "The previous processing worker has finished or stopped. "
                   "Queued, never-sent posts can be resumed with explicit approval."
                   if stage == "NEEDS_ATTENTION" and totals["queued"] and budget["available"]
              else "The current AI request allowance is exhausted."
                   if stage == "NEEDS_ATTENTION" and not budget["available"]
              else "")
    return {"run_id":run.id, "status":run.status,"stage":stage,
            "status_reason":reason,
            "posts_saved":int(run.result_count or 0), "total":len(ids),
            **totals,"progress_percent":round(100*totals["completed"]/len(ids)),
            "credits_used":int(run.credits_used or 0),
            "error":run.error_text or "", "budget":budget}


def _scope_ids(db, principal, campaign_id, limit=500):
    from .models import SocialListeningResult
    from .socialcrawl import _result_in_scope
    links = (db.query(CampaignEvidence, SocialListeningResult)
             .join(SocialListeningResult,
                   SocialListeningResult.id == CampaignEvidence.result_id)
             .filter(CampaignEvidence.campaign_id == int(campaign_id),
                     CampaignEvidence.match_method != "WATCHLIST_ACCOUNT")
             .order_by(CampaignEvidence.id.desc()).limit(limit).all())
    return list(dict.fromkeys(int(post.id) for _,post in links
                              if _result_in_scope(db, principal, post)))


def start_all(db, principal, campaign_id, payload):
    """Explicitly consented, idempotent campaign-level Assess All (no crawl)."""
    if not str(campaign_id or "").isdigit():
        raise ValueError("Select a campaign")
    if (payload or {}).get("confirm_ai_cost") is not True:
        raise ValueError("Confirm paid AI assessment costs before starting")
    c = (db.query(MonitoringCampaign)
         .filter(MonitoringCampaign.id == int(campaign_id)).with_for_update().first())
    if not c or not allowed(principal, c):
        raise PermissionError("Campaign unavailable")
    if not (principal.get("role") == "National Administrator" and has(principal, "administration")
            or str(c.created_by) == str(principal.get("id")) and has(principal, "add_intelligence")):
        raise PermissionError("Campaign editor permission required")
    active = (db.query(SocialListeningRun).join(
        CampaignRun, CampaignRun.social_listening_run_id == SocialListeningRun.id)
        .filter(CampaignRun.campaign_id == c.id,
                SocialListeningRun.provider == "AI_ASSESS_ALL",
                SocialListeningRun.status.in_(("QUEUED","RUNNING"))).first())
    if active:
        return {"started":False,"run_id":active.id,"already_active":True}
    ids = _scope_ids(db, principal, c.id)
    candidates = [rid for rid in ids if needs_full_assessment(_latest(db,c.id,rid))]
    jobs = {j.result_id:j for j in db.query(AIAssessmentJob).filter(
        AIAssessmentJob.campaign_id == c.id,
        AIAssessmentJob.result_id.in_(candidates)).all()} if candidates else {}
    eligible = [rid for rid in candidates
                if rid not in jobs or jobs[rid].state == "PENDING"]
    budget = remaining_budget(db, c.id)
    if not budget["provider_ready"] or not budget["database_ready"] or not budget["per_run"]:
        raise ValueError("AI provider, per-run limit or protected database budget unavailable")
    if eligible and budget["available"] <= 0:
        raise ValueError("AI request budget is exhausted. The remaining posts can be "
                         "assessed once the daily allowance is restored.")
    if not candidates:
        return {"started":False,"no_unassessed":True,"remaining":0}
    run = SocialListeningRun(provider="AI_ASSESS_ALL",status="QUEUED",
        executed_by=str(principal.get("id") or ""),
        result_count=len(candidates),credits_used=0,
        query_json=json.dumps({"campaign_id":c.id,"assessment_result_ids":candidates,
                               "source":"ASSESS_ALL","cost_confirmed":True}))
    db.add(run);db.flush()
    db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=run.id,
                       triggered_by="AI_ASSESS_ALL"))
    db.commit()
    return {"started":True,"run_id":run.id,"queued":len(eligible),
            "total":len(candidates),"request_budget_remaining":budget["available"],
            "socialcrawl_credits":0}


def execute_run(run_id):
    """Durably queue then assess each post; interrupted/failed calls are never auto-retried."""
    from .db import SessionLocal
    from .auto_relevance import assess_pending_campaign
    from .models import SocialListeningRun
    db = SessionLocal()
    ids = []
    campaign_id = None
    try:
        run = db.get(SocialListeningRun,int(run_id))
        if not run or run.provider not in ("SOCIALCRAWL_PRISM","AI_ASSESS_ALL"):
            return
        meta = json.loads(run.query_json or "{}")
        if not meta.get("cost_confirmed") and run.provider == "AI_ASSESS_ALL":
            return
        campaign_id = int(meta["campaign_id"])
        ids = [int(x) for x in meta.get("assessment_result_ids",[])[:500]
               if str(x).isdigit()]
        meta["assessment_worker_complete"] = False
        run.query_json = json.dumps(meta,ensure_ascii=False)
        if run.provider == "AI_ASSESS_ALL":
            run.status = "RUNNING"
        for rid in ids:
            previous = _latest(db,campaign_id,rid)
            if not needs_full_assessment(previous):
                continue
            job = (db.query(AIAssessmentJob).filter_by(
                campaign_id=campaign_id,result_id=rid).first())
            if not job:
                db.add(AIAssessmentJob(campaign_id=campaign_id,result_id=rid,
                                       state="PENDING",attempts=0))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    for rid in ids:
        db = SessionLocal()
        try:
            previous = _latest(db,campaign_id,rid)
            job = db.query(AIAssessmentJob).filter_by(
                campaign_id=campaign_id,result_id=rid).first()
            # No retry of a failed or ambiguous provider request.
            if not needs_full_assessment(previous) or not job or job.state != "PENDING":
                continue
        finally:
            db.close()
        # Do not claim and exhaust pending jobs when the budget has been used.
        # They remain PENDING for explicit, consented resumption later.
        quota_db = SessionLocal()
        try:
            budget = remaining_budget(quota_db,campaign_id)
        finally:
            quota_db.close()
        if not budget["available"] or not budget["provider_ready"]:
            break
        assess_pending_campaign(campaign_id,requested_limit=1,target_result_id=rid)
    db = SessionLocal()
    try:
        run=db.get(SocialListeningRun,int(run_id))
        if run:
            meta=json.loads(run.query_json or "{}")
            meta["assessment_worker_complete"]=True
            run.query_json=json.dumps(meta,ensure_ascii=False)
            if run.provider == "AI_ASSESS_ALL":run.status="COMPLETED"
            db.commit()
        from .inbox_read_cache import invalidate
        invalidate()
        try:
            from .smart_radar import invalidate_dashboard_cache
            invalidate_dashboard_cache()
        except (ImportError, AttributeError):
            pass
    finally:
        db.close()
