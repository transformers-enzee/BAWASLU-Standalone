"""No-cost, idempotent enqueue of unassessed ordinary campaign evidence.

Call only after an authorized campaign editor invokes reconciliation, or an
already-guarded AI worker invokes its existing enqueue step. No provider call,
no automatic retry of FAILED/COMPLETED jobs and no watchlist-account work.
"""
from sqlalchemy import and_, func, or_
from .models import CampaignEvidence, EvidenceAssessment, AIAssessmentJob

BATCH_LIMIT=200

def enqueue_unassessed_campaign_jobs(db,campaign_id,limit=BATCH_LIMIT):
    """Insert only missing job rows, oldest-first, in at most one batch.

    The latest saved relevance assessment decides eligibility. A historical
    row with UNASSESSED status remains eligible; an older UNASSESSED version
    superseded by a real classification is excluded. The database's unique
    campaign/result constraint resolves races without paying for anything.
    """
    cid=int(campaign_id)
    if type(limit) is not int or not 1<=limit<=BATCH_LIMIT:
        raise ValueError("Choose 1–200 pending assessment jobs per reconciliation")
    latest_id=(db.query(EvidenceAssessment.id).filter(
        EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
        EvidenceAssessment.result_id==CampaignEvidence.result_id
    ).order_by(EvidenceAssessment.assessment_version.desc(),
               EvidenceAssessment.id.desc()).limit(1)
      .correlate(CampaignEvidence).scalar_subquery())
    relevance=func.upper(func.coalesce(EvidenceAssessment.relevance_label,""))
    candidate_rows=(db.query(CampaignEvidence.result_id)
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .outerjoin(AIAssessmentJob,and_(
            AIAssessmentJob.campaign_id==CampaignEvidence.campaign_id,
            AIAssessmentJob.result_id==CampaignEvidence.result_id))
        .filter(CampaignEvidence.campaign_id==cid,
                CampaignEvidence.match_method!="WATCHLIST_ACCOUNT",
                or_(EvidenceAssessment.id.is_(None),
                    relevance.in_(["UNASSESSED",""])),
                AIAssessmentJob.id.is_(None))
        .order_by(CampaignEvidence.id.asc()).limit(limit).all())
    ids=[int(rid) for (rid,) in candidate_rows]
    if not ids:return 0
    values=[{"campaign_id":cid,"result_id":rid,"state":"PENDING",
             "attempts":0} for rid in ids]
    dialect=db.bind.dialect.name
    if dialect=="postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect=="sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise RuntimeError("Job reconciliation requires a conflict-safe database")
    stmt=insert(AIAssessmentJob).values(values).on_conflict_do_nothing(
        index_elements=["campaign_id","result_id"])
    result=db.execute(stmt)
    db.commit()
    return max(0,int(result.rowcount or 0))

def pending_campaign_job_links(db,campaign_id,limit=BATCH_LIMIT):
    """Return only queued, claimable ordinary evidence, oldest first.

    Read-only. Unlike the former latest-300-link scan, this selects directly
    from durable pending jobs, including evidence outside the UI window.
    Failed/completed/processing jobs and WATCHLIST_ACCOUNT matches are excluded.
    """
    cid=int(campaign_id)
    if type(limit) is not int or not 1<=limit<=BATCH_LIMIT:
        raise ValueError("Choose 1-200 queued assessment jobs per batch")
    return (db.query(CampaignEvidence)
        .join(AIAssessmentJob,and_(
            AIAssessmentJob.campaign_id==CampaignEvidence.campaign_id,
            AIAssessmentJob.result_id==CampaignEvidence.result_id))
        .filter(CampaignEvidence.campaign_id==cid,
                CampaignEvidence.match_method!="WATCHLIST_ACCOUNT",
                AIAssessmentJob.state=="PENDING",
                AIAssessmentJob.attempts<3)
        .order_by(CampaignEvidence.id.asc()).limit(limit).all())
