"""No-credit interrupted-job review and deliberate quarantine.

The cutoff is measured at execution time. A possibly billed request is NEVER
returned to PENDING. Ordinary WATCHLIST_ACCOUNT links are excluded, and
the existing campaign action gate must authorize callers before invocation.
"""
from datetime import datetime,timedelta
from sqlalchemy import and_,func,update,exists,case
from .models import AIAssessmentJob,CampaignEvidence

_GRACE=timedelta(minutes=10)
_REASON='Interrupted assessment: provider call status unknown; manual review required'

def _stale_query(db,campaign_id,cutoff):
    return (db.query(AIAssessmentJob.id)
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==int(campaign_id),
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                AIAssessmentJob.state=='PROCESSING',
                AIAssessmentJob.updated_at<cutoff))

def interrupted_campaign_preview(db,campaign_id):
    cutoff=datetime.utcnow()-_GRACE
    count=_stale_query(db,campaign_id,cutoff).count()
    # Read only aggregate lifecycle states; never return post IDs or errors.
    rows=(db.query(
        AIAssessmentJob.state,
        func.count(AIAssessmentJob.id),
        func.coalesce(func.sum(case((
            and_(AIAssessmentJob.state=='FAILED',
                 AIAssessmentJob.last_error==_REASON),1),else_=0)),0))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==int(campaign_id),
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT')
        .group_by(AIAssessmentJob.state).all())
    by_state={str(state):int(n) for state,n,_ in rows}
    quarantined=sum(int(n) for _,_,n in rows)
    return {'campaign_id':str(int(campaign_id)),
            'stale_processing_jobs':count,
            'processing_not_stale':max(0,by_state.get('PROCESSING',0)-count),
            'already_quarantined_for_manual_review':quarantined,
            'other_failed_jobs':max(0,by_state.get('FAILED',0)-quarantined),
            'pending_jobs':by_state.get('PENDING',0),
            'completed_jobs':by_state.get('COMPLETED',0),
            'superseded_assessed_jobs':by_state.get('SUPERSEDED_ASSESSED',0),
            'total_ordinary_jobs':sum(by_state.values()),
            'grace_minutes':10,'quarantine_state':'FAILED',
            'provider_call_status':'UNKNOWN',
            'safe_to_retry_automatically':False,
            'requires_explicit_confirmation':True,
            'source_text_or_ids_returned':False,
            'paid_provider_called':False,'database_writes':0}

def quarantine_interrupted_campaign_jobs(db,campaign_id,limit=100):
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('Choose a quarantine limit from 1 to 100')
    now=datetime.utcnow()
    cutoff=now-_GRACE
    # Bulk selects eligible IDs, but the guarded UPDATE revalidates state and
    # timestamp under any concurrent worker. No job is retried or billed.
    ids=[row[0] for row in _stale_query(db,campaign_id,cutoff)
         .order_by(AIAssessmentJob.id.asc()).limit(limit).all()]
    if not ids:
        return {'campaign_id':str(int(campaign_id)),
                'quarantined_jobs':0,'state':'FAILED',
                'remaining_stale_jobs':0,
                'requires_manual_history_review':False,
                'automatically_retried':False,'paid_provider_called':False,
                'source_text_or_ids_returned':False}
    # A second association test prevents a stale race against an unrelated
    # campaign even if the ID list was incorrectly composed.
    stmt=(update(AIAssessmentJob)
        .where(AIAssessmentJob.id.in_(ids),
               AIAssessmentJob.campaign_id==int(campaign_id),
               AIAssessmentJob.state=='PROCESSING',
               AIAssessmentJob.updated_at<cutoff,
               exists().where(and_(
                   CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
                   CampaignEvidence.result_id==AIAssessmentJob.result_id,
                   CampaignEvidence.match_method!='WATCHLIST_ACCOUNT')))
        .values(state='FAILED',last_error=_REASON,updated_at=now))
    try:
        changed=db.execute(stmt).rowcount
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'campaign_id':str(int(campaign_id)),
            'quarantined_jobs':int(changed),
            'remaining_stale_jobs':_stale_query(db,campaign_id,cutoff).count(),
            'state':'FAILED','requires_manual_history_review':bool(changed),
            'automatically_retried':False,'paid_provider_called':False,
            'source_text_or_ids_returned':False}
