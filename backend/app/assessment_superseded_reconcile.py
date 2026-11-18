"""Explicit, no-provider reconciliation of stale PENDING jobs already assessed."""
from datetime import datetime
from sqlalchemy import and_,func,update
from .models import AIAssessmentJob,CampaignEvidence,EvidenceAssessment
_STATE='SUPERSEDED_ASSESSED'
_LABELS=('RELEVANT','IRRELEVANT','UNCERTAIN')
_REASON='Already classified in saved evidence; queue superseded without provider call'

def _latest_id(db):
    return (db.query(EvidenceAssessment.id).filter(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).limit(1)
        .correlate(AIAssessmentJob).scalar_subquery())

def _eligible(db,cid):
    latest_id=_latest_id(db)
    return (db.query(AIAssessmentJob.id)
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .join(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .filter(AIAssessmentJob.campaign_id==int(cid),
                AIAssessmentJob.state=='PENDING',
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).in_(_LABELS)))

def superseded_preview(db,campaign_id):
    return {'campaign_id':str(int(campaign_id)),
            'already_assessed_pending_jobs':_eligible(db,campaign_id).count(),
            'new_state':_STATE,'requested_ai_calls':0,
            'requires_explicit_confirmation':True,
            'already_assessed_is_not_new_ai_completion':True,
            'recorded_provider_usage_unchanged':True,
            'paid_provider_called':False,'database_writes':0,
            'source_ids_returned':False}

def apply_superseded_reconciliation(db,campaign_id,limit=100):
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('Queue reconciliation limit must be between 1 and 100')
    cid=int(campaign_id)
    ids=[row[0] for row in _eligible(db,cid).order_by(AIAssessmentJob.id.asc()).limit(limit).all()]
    if not ids:
        return {'campaign_id':str(cid),'superseded_jobs':0,'remaining_eligible':0,
                'state':_STATE,'paid_provider_called':False,'ai_requests':0}
    # Revalidate latest assessment, campaign link and PENDING state in UPDATE.
    latest_id=_latest_id(db)
    approved=(db.query(EvidenceAssessment.id)
        .filter(EvidenceAssessment.id==latest_id,
                func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).in_(_LABELS))
        .correlate(AIAssessmentJob).exists())
    linked=(db.query(CampaignEvidence.id)
        .filter(CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
                CampaignEvidence.result_id==AIAssessmentJob.result_id,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT')
        .correlate(AIAssessmentJob).exists())
    stmt=(update(AIAssessmentJob)
        .where(AIAssessmentJob.id.in_(ids),
               AIAssessmentJob.campaign_id==cid,
               AIAssessmentJob.state=='PENDING',approved,linked)
        .values(state=_STATE,last_error=_REASON,updated_at=datetime.utcnow()))
    try:
        changed=int(db.execute(stmt).rowcount)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {'campaign_id':str(cid),'superseded_jobs':changed,
            'remaining_eligible':_eligible(db,cid).count(),
            'state':_STATE,'paid_provider_called':False,'ai_requests':0}
