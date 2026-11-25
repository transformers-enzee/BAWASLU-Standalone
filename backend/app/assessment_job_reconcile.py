"""No-cost, idempotent enqueue of unassessed ordinary campaign evidence.

Call only after an authorized campaign editor invokes reconciliation, or an
already-guarded AI worker invokes its existing enqueue step. No provider call,
no automatic retry of FAILED/COMPLETED jobs and no watchlist-account work.
"""
from datetime import datetime
from sqlalchemy import and_, func, or_, case
from .models import CampaignEvidence, EvidenceAssessment, AIAssessmentJob

BATCH_LIMIT=200
_PRELIMINARY=('PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER')

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
    ).order_by(case((func.upper(func.coalesce(EvidenceAssessment.model_version,'')).in_(_PRELIMINARY),1),else_=0).asc(),
               EvidenceAssessment.assessment_version.desc(),
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
                    relevance.in_(["UNASSESSED",""]),
                    func.upper(func.coalesce(EvidenceAssessment.model_version,"")).in_(_PRELIMINARY)),
                AIAssessmentJob.id.is_(None))
        .order_by(CampaignEvidence.id.asc()).limit(limit).all())
    ids=[int(rid) for (rid,) in candidate_rows]
    if not ids:return 0
    # Explicit values are required for reconciliation SQL paths: some existing
    # PostgreSQL installations have NOT NULL columns without server defaults.
    # Never depend on ORM-only defaults for bulk insertion.
    now=datetime.utcnow()
    values=[{"campaign_id":cid,"result_id":rid,"state":"PENDING",
             "attempts":0,"last_error":"","created_at":now,"updated_at":now}
            for rid in ids]
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

def pending_campaign_job_links(db,campaign_id,limit=BATCH_LIMIT,result_ids=None):
    """Return only queued, claimable ordinary evidence, oldest first.

    Read-only. Unlike the former latest-300-link scan, this selects directly
    from durable pending jobs, including evidence outside the UI window.
    Failed/completed/processing jobs, previously assessed sources, and\n    WATCHLIST_ACCOUNT matches are excluded. The worker retains its final\n    atomic claim and saved-assessment recheck before any provider call.
    """
    cid=int(campaign_id)
    if type(limit) is not int or not 1<=limit<=BATCH_LIMIT:
        raise ValueError("Choose 1-200 queued assessment jobs per batch")
    # Match readiness and the worker's final assessed-label guard BEFORE
    # LIMIT. Otherwise a page of already-completed pending jobs can crowd out
    # genuinely unassessed, claimable evidence older in the durable queue.
    latest_id=(db.query(EvidenceAssessment.id)
        .filter(EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
                EvidenceAssessment.result_id==CampaignEvidence.result_id)
        .order_by(case((func.upper(func.coalesce(EvidenceAssessment.model_version,'')).in_(_PRELIMINARY),1),else_=0).asc(),
                  EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).limit(1)
        .correlate(CampaignEvidence).scalar_subquery())
    unassessed=or_(EvidenceAssessment.id.is_(None),
        func.upper(func.coalesce(EvidenceAssessment.relevance_label,""))
            .notin_(["RELEVANT","HIGHLY_RELEVANT","IRRELEVANT","UNCERTAIN"]),
        func.upper(func.coalesce(EvidenceAssessment.model_version,"")).in_(_PRELIMINARY))
    scoped=([CampaignEvidence.result_id.in_(result_ids)] if result_ids is not None else [])
    return (db.query(CampaignEvidence)
        .join(AIAssessmentJob,and_(
            AIAssessmentJob.campaign_id==CampaignEvidence.campaign_id,
            AIAssessmentJob.result_id==CampaignEvidence.result_id))
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .filter(CampaignEvidence.campaign_id==cid,
                CampaignEvidence.match_method!="WATCHLIST_ACCOUNT",
                AIAssessmentJob.state=="PENDING",
                AIAssessmentJob.attempts<3,
                unassessed,*scoped)
        .order_by(CampaignEvidence.id.asc()).limit(limit).all())


def enqueue_scoped_jobs(db,campaign_id,result_ids):
    """Queue authorized run IDs in bounded, conflict-safe batches, without billing."""
    if not result_ids:return 0
    if len(result_ids)>BATCH_LIMIT:raise ValueError("Scoped queue batch exceeds 200")
    cid=int(campaign_id)
    latest_id=(db.query(EvidenceAssessment.id).filter(
        EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
        EvidenceAssessment.result_id==CampaignEvidence.result_id)
        .order_by(case((func.upper(func.coalesce(EvidenceAssessment.model_version,'')).in_(_PRELIMINARY),1),else_=0).asc(),
                  EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc())
        .limit(1).correlate(CampaignEvidence).scalar_subquery())
    rows=(db.query(CampaignEvidence.result_id)
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .outerjoin(AIAssessmentJob,and_(AIAssessmentJob.campaign_id==CampaignEvidence.campaign_id,
                                      AIAssessmentJob.result_id==CampaignEvidence.result_id))
        .filter(CampaignEvidence.campaign_id==cid,CampaignEvidence.result_id.in_(result_ids),
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',AIAssessmentJob.id.is_(None),
                or_(EvidenceAssessment.id.is_(None),
                    func.upper(func.coalesce(EvidenceAssessment.model_version,'')).in_(_PRELIMINARY),
                    func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).notin_(['RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN']))).all())
    if not rows:return 0
    now=datetime.utcnow()
    values=[dict(campaign_id=cid,result_id=rid,state='PENDING',attempts=0,last_error='',created_at=now,updated_at=now) for rid, in rows]
    if db.bind.dialect.name=='postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif db.bind.dialect.name=='sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:raise RuntimeError('Conflict-safe database required')
    result=db.execute(insert(AIAssessmentJob).values(values).on_conflict_do_nothing(index_elements=['campaign_id','result_id']))
    db.commit()
    return max(0,int(result.rowcount or 0))
