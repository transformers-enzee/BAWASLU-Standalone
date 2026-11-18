"""v168.4 all five lifecycle states and partitioned recovery are reconciled."""
from datetime import datetime,timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob
from app.assessment_snapshot_consistency import assessment_snapshot_consistency
from app.campaign_ai_readiness import campaign_ai_worker_readiness
from app.assessment_completion_audit import campaign_completion_audit
from app.assessment_interrupted_recovery import interrupted_campaign_preview,_REASON
from app.assessment_superseded_reconcile import superseded_preview
from app.assessment_operations_overview import campaign_assessment_operations_overview

def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def add(db,cid,rid,state,age_minutes=0,reason=None):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method='KEYWORD'))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=1,
        updated_at=datetime.utcnow()-timedelta(minutes=age_minutes),
        last_error=reason))
    db.flush()

def aggregates(db,cid):
    return (
        campaign_ai_worker_readiness(db,cid,env={}),
        campaign_completion_audit(db,cid),
        interrupted_campaign_preview(db,cid),
        superseded_preview(db,cid))

def test_full_lifecycle_counts_with_stale_and_quarantined_jobs():
    engine,db=fixture()
    try:
        add(db,4,1,'PENDING')
        add(db,4,2,'PROCESSING',age_minutes=2)
        add(db,4,3,'PROCESSING',age_minutes=30)
        add(db,4,4,'COMPLETED')
        add(db,4,5,'FAILED',reason='ordinary failure')
        add(db,4,6,'FAILED',reason=_REASON)
        add(db,4,7,'SUPERSEDED_ASSESSED')
        add(db,2,8,'PROCESSING',age_minutes=30)
        r,c,i,s=aggregates(db,4)
        assert i['stale_processing_jobs']==1
        assert i['processing_not_stale']==1
        assert i['already_quarantined_for_manual_review']==1
        assert i['other_failed_jobs']==1
        parity=assessment_snapshot_consistency(r,c,i,s)
        assert parity['all_consistent'],parity['failed_checks']
        assert all(parity['checks'].values())
        assert len(parity['validated_queue_states'])==5
        assert parity['new_database_queries']==0
        o=campaign_assessment_operations_overview(db,4)
        assert not any(x['code']=='SNAPSHOT_AGGREGATE_DRIFT' for x in o['issues'])
        assert o['operational_acceptance']['status']=='HOLD_FOR_HISTORY_REVIEW'
        assert o['paid_provider_called'] is False and o['database_writes']==0
        assert aggregates(db,2)[2]['stale_processing_jobs']==1
    finally:db.close();engine.dispose()

def test_partition_drift_detected_without_database_corruption_claim():
    engine,db=fixture()
    try:
        add(db,4,1,'PROCESSING',age_minutes=30)
        add(db,4,2,'FAILED',reason=_REASON)
        r,c,i,s=aggregates(db,4)
        i['already_quarantined_for_manual_review']=0
        parity=assessment_snapshot_consistency(r,c,i,s)
        assert not parity['all_consistent']
        assert 'worker_vs_interrupted_per_state' in parity['failed_checks']
        assert 'interrupted_internal_state_total' in parity['failed_checks']
        assert parity['database_corruption_proven'] is False
    finally:db.close();engine.dispose()

def test_active_processing_is_not_mislabeled_as_waiting():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'app'/'assessment_operations_overview.py').read_text()
    assert text.index("'PROCESSING' if readiness['queue_counts']['processing']") < text.index(
        "'AWAITING_PROCESSING' if readiness['queue_counts']['pending']")
