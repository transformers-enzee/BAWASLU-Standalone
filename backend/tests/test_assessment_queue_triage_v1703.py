"""v170.3: no-cost operational queue partition/triage acceptance."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from datetime import datetime,timedelta
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,SocialListeningResult
from app.assessment_operations_overview import campaign_assessment_operations_overview
from app.assessment_queue_triage import assessment_queue_triage
from app.assessment_interrupted_recovery import _REASON


def fixture():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    return e,Session(e)


def seed(db,cid,rid,state='PENDING',text='fixture',label=None,age=0,
         error='',method='KEYWORD',attempts=0):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    db.add(SocialListeningResult(id=rid,run_id=1,text_content=text))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,
        attempts=attempts,last_error=error,
        updated_at=datetime.utcnow()-timedelta(minutes=age)))
    if label is not None:
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
            assessment_version=1,relevance_label=label))
    db.flush()


def test_queue_triage_partition_is_read_only_and_campaign_scoped():
    e,db=fixture()
    try:
        seed(db,40,1,'PROCESSING',age=25)
        seed(db,40,2,'PROCESSING',age=1)
        seed(db,40,3,'FAILED',error=_REASON)
        seed(db,40,4,'FAILED',error='other failure')
        seed(db,40,5,'SUPERSEDED_ASSESSED',label='RELEVANT')
        seed(db,40,6,'COMPLETED',label='RELEVANT')
        seed(db,40,7,'PENDING')
        seed(db,40,8,'PENDING',text=' ')
        seed(db,40,9,'PENDING',label='HIGHLY_RELEVANT')
        seed(db,40,10,'PENDING',attempts=3)
        seed(db,40,11,'PENDING',method='WATCHLIST_ACCOUNT')
        seed(db,41,12,'PROCESSING',age=25)
        before=[(x.id,x.state,x.last_error) for x in db.query(AIAssessmentJob).order_by(AIAssessmentJob.id)]
        out=campaign_assessment_operations_overview(db,40)
        q=out['queue_triage']
        groups={x['code']:x['count'] for x in q['buckets']}
        assert groups=={'STALE_PROCESSING':1,'QUARANTINED_INTERRUPTED':1,
            'FAILED_OTHER':1,'SUPERSEDED_ASSESSED':1,
            'PROCESSING_ACTIVE':1,'PENDING':4,'COMPLETED':1}
        assert q['ordinary_job_total']==10 and q['bucket_total']==10
        assert q['buckets_partition_all_jobs']
        assert q['pending_breakdown']=={
            'pending_total':4,'eligible_with_text':1,
            'missing_source_or_text':1,'already_assessed':1,
            'attempt_limit_exhausted':1,'breakdown_total':4,
            'breakdown_reconciled':True}
        assert q['status']=='HOLD_FOR_HISTORY_REVIEW'
        assert q['paid_provider_called'] is False and q['database_writes']==0
        assert q['automatically_retried'] is False
        assert [(x.id,x.state,x.last_error) for x in db.query(AIAssessmentJob).order_by(AIAssessmentJob.id)]==before
    finally:db.close();e.dispose()


def test_triage_not_confuse_empty_active_queue_with_completed_audit():
    r={'queue_counts':{'claimable_pending_with_text':0,
        'pending_missing_source_or_text':0,'pending_attempts_exhausted':0},
        'pending_already_assessed_excluded_from_ai':0}
    recovery={'pending_jobs':0,'stale_processing_jobs':0,'processing_not_stale':0,
        'already_quarantined_for_manual_review':0,'other_failed_jobs':0,
        'superseded_assessed_jobs':2,'completed_jobs':3,'total_ordinary_jobs':5,
        'grace_minutes':10}
    q=assessment_queue_triage(r,recovery,{'superseded_without_current_classification':0})
    assert q['status']=='NO_ACTIVE_WORK'
    assert q['ordinary_job_total']==5
    assert q['historical_provider_usage_not_verified'] is True
    assert not q['automatic_paid_ai_authorized']


def test_mismatched_nonatomic_snapshots_fail_closed():
    r={'queue_counts':{'claimable_pending_with_text':2,
        'pending_missing_source_or_text':0,'pending_attempts_exhausted':0},
        'pending_already_assessed_excluded_from_ai':0}
    recovery={'pending_jobs':1,'stale_processing_jobs':0,'processing_not_stale':0,
        'already_quarantined_for_manual_review':0,'other_failed_jobs':0,
        'superseded_assessed_jobs':0,'completed_jobs':0,'total_ordinary_jobs':1}
    q=assessment_queue_triage(r,recovery,{})
    assert q['status']=='RECHECK_INDEPENDENT_SNAPSHOTS'
    assert not q['pending_breakdown']['breakdown_reconciled']
    assert q['database_writes']==0 and not q['paid_provider_called']


def test_pending_assessed_and_missing_text_remain_distinct():
    r={'queue_counts':{'claimable_pending_with_text':0,
        'pending_missing_source_or_text':1,'pending_attempts_exhausted':0},
        'pending_already_assessed_excluded_from_ai':1}
    recovery={'pending_jobs':2,'stale_processing_jobs':0,'processing_not_stale':0,
        'already_quarantined_for_manual_review':0,'other_failed_jobs':0,
        'superseded_assessed_jobs':0,'completed_jobs':0,'total_ordinary_jobs':2}
    q=assessment_queue_triage(r,recovery,{})
    assert q['status']=='QUEUE_RECONCILIATION'
    assert q['pending_breakdown']['breakdown_reconciled']
    assert q['pending_breakdown']['eligible_with_text']==0
