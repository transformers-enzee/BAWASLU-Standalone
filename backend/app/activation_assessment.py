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
    """Read explicitly configured request allowances; no embedded maximum."""
    from .models import AIBudgetReservation
    def cap(name, maximum):
        try:
            return max(0, int(os.getenv(name, "0")))
        except (TypeError, ValueError):
            return 0
    daily = cap("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN", 1000)
    lifetime = cap("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN", 5000)
    per_run = cap("BAWASLU_AI_ASSESSMENTS_PER_RUN", 50)
    rows = db.query(AIBudgetReservation).filter(
        AIBudgetReservation.campaign_id == int(campaign_id)).all()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    reserved = {r.budget_period: int(r.reserved_requests or 0) for r in rows}
    provider_ready=bool(os.getenv("OPENAI_API_KEY", "").strip())
    database_ready=db.bind.dialect.name == "postgresql"
    daily_remaining=max(0,daily-reserved.get(today,0))
    lifetime_remaining=max(0,lifetime-reserved.get("lifetime",0))
    blockers=[]
    if not provider_ready:blockers.append("AI_PROVIDER_NOT_CONFIGURED")
    if not database_ready:blockers.append("PROTECTED_DATABASE_REQUIRED")
    if not daily:blockers.append("DAILY_LIMIT_NOT_CONFIGURED")
    elif not daily_remaining:blockers.append("DAILY_LIMIT_EXHAUSTED")
    if not lifetime:blockers.append("LIFETIME_LIMIT_NOT_CONFIGURED")
    elif not lifetime_remaining:blockers.append("LIFETIME_LIMIT_EXHAUSTED")
    if not per_run:blockers.append("PER_RUN_LIMIT_NOT_CONFIGURED")
    return {"available":min(daily_remaining,lifetime_remaining),
            "daily_limit":daily,"lifetime_limit":lifetime,"per_run":per_run,
            "daily_remaining":daily_remaining,"lifetime_remaining":lifetime_remaining,
            "provider_ready":provider_ready,"database_ready":database_ready,"blockers":blockers}


def budget_blocker_message(budget):
    labels={"AI_PROVIDER_NOT_CONFIGURED":"AI provider is not configured.",
            "PROTECTED_DATABASE_REQUIRED":"Protected PostgreSQL budget storage is unavailable.",
            "DAILY_LIMIT_NOT_CONFIGURED":"Daily AI request limit is zero or not configured.",
            "DAILY_LIMIT_EXHAUSTED":"Daily AI request allowance is exhausted.",
            "LIFETIME_LIMIT_NOT_CONFIGURED":"Lifetime AI request limit is zero or not configured.",
            "LIFETIME_LIMIT_EXHAUSTED":"Lifetime AI request allowance is exhausted.",
            "PER_RUN_LIMIT_NOT_CONFIGURED":"Per-run AI request limit is zero or not configured."}
    return " ".join(labels[x] for x in budget.get("blockers",[]) if x in labels)


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
    if run.provider=='SOCIALCRAWL_PRISM' and run.status in ('QUEUED','RUNNING'):
        from .prism_discover import heartbeat_stale
        if heartbeat_stale(run,meta):
            return {'run_id':run.id,'status':run.status,'stage':'NEEDS_ATTENTION','posts_saved':int(run.result_count or 0),
                'total':0,'completed':0,'queued':0,'processing':0,'failed':0,'blocked':0,'progress_percent':0,
                'credits_used':int(run.credits_used or 0),'status_reason':'Collection worker stopped updating. Open the project dashboard to recover or quarantine the original run; no new crawl was started.',
                'collection_diagnostics':meta.get('collection_diagnostics') or {},'budget':remaining_budget(db,c.id)}
    ids = [int(x) for x in (meta.get("assessment_result_ids", []) if meta.get("full_collection") else meta.get("assessment_result_ids", [])[:500])
           if str(x).isdigit()]
    diag=meta.get("collection_diagnostics")
    if not isinstance(diag,dict):diag={}
    if run.provider=="SOCIALCRAWL_PRISM" and not diag:
        # Old provider runs did not save precise candidate diagnostics.
        # A stored-row count only represents newly inserted source rows.
        from .models import SocialListeningResult
        saved_rows=db.query(SocialListeningResult.id).filter(SocialListeningResult.run_id==run.id).count()
        diag={'newly_saved_source_rows':saved_rows,
              'accepted_boolean_matches':int(run.result_count or 0),
              'counts_basis':'legacy_new_source_rows_only'}
    if not ids:
        stage = ("FAILED" if run.status == "FAILED" else
                 "COLLECTING" if run.status in ("QUEUED", "RUNNING") else
                 "NO_NEW_POSTS")
        return {"run_id":run.id,"status":run.status,"stage":stage,
                "posts_saved":int(run.result_count or 0),"total":0,"completed":0,
                "queued":0,"processing":0,"failed":0,"blocked":0,
                "progress_percent":0,"credits_used":int(run.credits_used or 0),
                "collection_diagnostics":diag,
                "status_reason":("Provider returned source rows, but none entered this monitoring project. "
                                 "Local search matching may have excluded all candidates; provider credits still apply."
                                 if run.provider=="SOCIALCRAWL_PRISM" and
                                    int(diag.get('raw_provider_items') or diag.get('newly_saved_source_rows') or 0)>0
                                    and not int(run.result_count or 0) else ""),
                "error":run.error_text or "", "budget":remaining_budget(db,c.id)}
    assessments = {}
    jobs = {}
    # Bound each database query; the run is not bounded to the first page.
    for offset in range(0,len(ids),500):
        chunk=ids[offset:offset+500]
        for row in (db.query(EvidenceAssessment).filter(
                EvidenceAssessment.campaign_id == c.id,
                EvidenceAssessment.result_id.in_(chunk))
                .order_by(__import__('sqlalchemy').case(
                    (EvidenceAssessment.model_version.in_(['PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER']),1),
                    else_=0).asc(),EvidenceAssessment.assessment_version.desc(),
                          EvidenceAssessment.id.desc()).all()):
            assessments.setdefault(row.result_id, row)
        jobs.update({j.result_id:j for j in db.query(AIAssessmentJob).filter(
            AIAssessmentJob.campaign_id == c.id, AIAssessmentJob.result_id.in_(chunk)).all()})
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
            elif job and job.state == "PENDING" and job.attempts<3:
                totals["queued"] += 1
            elif job and job.state == "PENDING":
                totals["failed"] += 1
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
                      or budget["available"] == 0 or not budget["per_run"]) else "ASSESSING")
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
    if stage=="NEEDS_ATTENTION" and totals["queued"] and not totals["stalled"]:
        reason=budget_blocker_message(budget) or ("Per-run request limit reached. Resume the saved queue without another crawl." if meta.get("assessment_worker_exit_reason")=="PER_RUN_LIMIT_REACHED" else reason)
    finished_at = [j.updated_at for j in jobs.values()
                   if j.state == "COMPLETED" and j.updated_at]
    last_activity = max(finished_at) if finished_at else None
    recent_cutoff = datetime.utcnow()-timedelta(minutes=10)
    recent_completed = sum(1 for j in jobs.values()
                           if j.state == "COMPLETED" and j.updated_at and j.updated_at>=recent_cutoff)
    throughput = round(recent_completed/10.0,2)
    eta_seconds = int((len(ids)-totals["completed"])/throughput*60) if throughput>0 and stage=="ASSESSING" and totals["processing"] else None
    return {"run_id":run.id, "status":run.status,"stage":stage,
            "last_activity_at":last_activity.isoformat()+"Z" if last_activity else None,
            "completed_per_minute":throughput,"eta_seconds":eta_seconds,
            "status_reason":reason,
            "assessment_worker_exit_reason":meta.get("assessment_worker_exit_reason"),
            "resume_available":bool(totals["queued"] and not totals["processing"] and not totals["stalled"] and not budget.get("blockers")),
            "posts_saved":int(run.result_count or 0), "total":len(ids),
            **totals,"progress_percent":round(100*totals["completed"]/len(ids)),
            "credits_used":int(run.credits_used or 0),
            "collection_diagnostics":diag,
            "error":run.error_text or "", "budget":budget}


def _scope_ids(db, principal, campaign_id, limit=None):
    """Select unassessed evidence throughout the project, not its latest 500 rows.

    Prefer dispatchable work and preserve blocked/ambiguous requests for status
    review. The authorized ID snapshot is processed in bounded database batches.
    """
    from .models import SocialListeningResult
    from .socialcrawl import _result_in_scope
    from sqlalchemy import case,func,or_,and_
    from types import SimpleNamespace
    latest_id=(db.query(EvidenceAssessment.id).filter(
        EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
        EvidenceAssessment.result_id==CampaignEvidence.result_id)
        .order_by(case((EvidenceAssessment.model_version.in_(['PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER']),1),else_=0).asc(),
            EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc())
        .limit(1).correlate(CampaignEvidence).scalar_subquery())
    incomplete=or_(EvidenceAssessment.id.is_(None),
        func.upper(func.coalesce(EvidenceAssessment.model_version,'')).in_(['PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER']),
        func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).notin_(['RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN']))
    dispatchable=and_(func.length(func.trim(func.coalesce(SocialListeningResult.text_content,'')))>0,
        or_(AIAssessmentJob.id.is_(None),and_(AIAssessmentJob.state=='PENDING',AIAssessmentJob.attempts<3)))
    rows=(db.query(CampaignEvidence.result_id,SocialListeningResult.run_id,
                   case((dispatchable,0),else_=1))
        .join(SocialListeningResult,SocialListeningResult.id==CampaignEvidence.result_id)
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .outerjoin(AIAssessmentJob,and_(AIAssessmentJob.campaign_id==CampaignEvidence.campaign_id,AIAssessmentJob.result_id==CampaignEvidence.result_id))
        .filter(CampaignEvidence.campaign_id==int(campaign_id),
            CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',incomplete)
        .order_by(case((dispatchable,0),else_=1),CampaignEvidence.id.asc()))
    if principal.get('geographic_scope')=='Nationwide':
        return [rid for rid,_,_ in (rows.limit(limit) if limit is not None else rows).yield_per(500)]
    ids=[];scope={}
    for rid,run_id,_ in rows.yield_per(200):
        if run_id not in scope:scope[run_id]=_result_in_scope(db,principal,SimpleNamespace(run_id=run_id))
        if scope[run_id]:ids.append(rid)
        if limit is not None and len(ids)>=limit:break
    return ids


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
    source_prefix = str((payload or {}).get("source_batch_prefix") or "")
    if source_prefix:
        # Explicitly scope this run to the verified 19-Nov ZocialEye import.
        # An operator must approve the metered action; this is not auto-discovery.
        if source_prefix != "offline-xlsx-20261119-batch-":
            raise ValueError("Unsupported source import batch")
        from .models import SocialListeningResult
        from .socialcrawl import _result_in_scope
        scoped_rows = (db.query(SocialListeningResult)
            .join(CampaignEvidence, CampaignEvidence.result_id == SocialListeningResult.id)
            .join(SocialListeningRun, SocialListeningRun.id == SocialListeningResult.run_id)
            .filter(CampaignEvidence.campaign_id == c.id,
                    CampaignEvidence.match_method != "WATCHLIST_ACCOUNT",
                    SocialListeningRun.provider == "ZOCIALEYE",
                    SocialListeningRun.provider_request_id.like(source_prefix + "%"))
            .order_by(SocialListeningResult.id).limit(501).all())
        if len(scoped_rows) > 500:
            raise ValueError("Import batch exceeds 500 posts; split before assessment")
        ids = list(dict.fromkeys(post.id for post in scoped_rows
                                if _result_in_scope(db, principal, post)))
    else:
        ids = _scope_ids(db, principal, c.id)
    candidates = [rid for rid in ids if needs_full_assessment(_latest(db,c.id,rid))] if source_prefix else ids
    jobs = {}
    for offset in range(0,len(candidates),500):
        jobs.update({j.result_id:j for j in db.query(AIAssessmentJob).filter(
            AIAssessmentJob.campaign_id == c.id,
            AIAssessmentJob.result_id.in_(candidates[offset:offset+500])).all()})
    eligible = [rid for rid in candidates
                if rid not in jobs or (jobs[rid].state == "PENDING" and jobs[rid].attempts<3)]
    budget = remaining_budget(db, c.id)
    if not budget["provider_ready"] or not budget["database_ready"] or not budget["per_run"]:
        raise ValueError(budget_blocker_message(budget) or "AI provider, per-run limit or protected database budget unavailable")
    if eligible and budget["available"] <= 0:
        raise ValueError("AI request budget is exhausted. The remaining posts can be "
                         "assessed once the daily allowance is restored.")
    if not candidates:
        return {"started":False,"no_unassessed":True,"remaining":0}
    run = SocialListeningRun(provider="AI_ASSESS_ALL",status="QUEUED",
        executed_by=str(principal.get("id") or ""),
        result_count=len(candidates),credits_used=0,
        query_json=json.dumps({"campaign_id":c.id,"assessment_result_ids":candidates,
                               "source":"ASSESS_ALL","source_batch_prefix":source_prefix,"cost_confirmed":True,"full_collection":True}))
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
        ids = [int(x) for x in (meta.get("assessment_result_ids",[]) if meta.get("full_collection") else meta.get("assessment_result_ids",[])[:500])
               if str(x).isdigit()]
        meta["assessment_worker_complete"] = False
        meta.pop("assessment_worker_exit_reason",None)
        run.query_json = json.dumps(meta,ensure_ascii=False)
        if run.provider == "AI_ASSESS_ALL":
            run.status = "RUNNING"
        db.commit()
        # Only IDs already authorized by the run may enter the queue. Bulk
        # insert is conflict-safe and never reopens previously claimed jobs.
        from .assessment_job_reconcile import enqueue_scoped_jobs
        for offset in range(0,len(ids),200):
            enqueue_scoped_jobs(db,campaign_id,ids[offset:offset+200])
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    attempted=0
    exit_reason="QUEUE_SCANNED"
    # Load only authorized, never-sent work per chunk. The worker's atomic
    # claim and protected request reservation remain the final authority.
    for offset in range(0,len(ids),200):
        db=SessionLocal()
        try:
            chunk=ids[offset:offset+200]
            budget=remaining_budget(db,campaign_id)
            from .assessment_job_reconcile import pending_campaign_job_links
            eligible=[link.result_id for link in pending_campaign_job_links(db,campaign_id,limit=200,result_ids=chunk)]
        finally:db.close()
        if not eligible:continue
        if not budget["available"] or not budget["provider_ready"] or not budget["database_ready"] or not budget["per_run"] or attempted>=budget['per_run']:
            exit_reason="BUDGET_OR_CONFIGURATION_BLOCKED" if budget.get("blockers") else "PER_RUN_LIMIT_REACHED"
            break
        batch=eligible[:min(budget['available'],budget['per_run']-attempted)]
        if not batch:break
        outcome=assess_pending_campaign(campaign_id,requested_limit=len(batch),target_result_ids=batch)
        if not isinstance(outcome,dict):
            exit_reason="WORKER_BUSY_OR_UNAVAILABLE"
            break
        attempted+=int(outcome.get('attempted') or 0)
        if outcome.get('provider_blocked'):
            exit_reason="PROVIDER_OR_BUDGET_BLOCKED"
            break
    db = SessionLocal()
    try:
        run=db.get(SocialListeningRun,int(run_id))
        if run:
            meta=json.loads(run.query_json or "{}")
            meta["assessment_worker_complete"]=True
            meta["assessment_worker_exit_reason"]=exit_reason
            meta["assessment_dispatch_attempts"]=attempted
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
