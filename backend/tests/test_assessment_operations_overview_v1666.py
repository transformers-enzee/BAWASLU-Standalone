"""v166.6 unified campaign operation inventory remains read-only and campaign scoped."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment
from app.assessment_operations_overview import campaign_assessment_operations_overview
from app import assessment_operations_overview as ops

def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def put(db,cid,rid,method='KEYWORD',state=None,assessed=False):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    if state is not None:
        db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=0))
    if assessed:
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
           assessment_version=1,relevance_label='RELEVANT'))
    db.flush()

def test_combined_view_without_expanding_campaign_scope(monkeypatch):
    e,db=fixture()
    try:
        put(db,2,1,state='PENDING')
        put(db,2,2)
        put(db,2,3,method='WATCHLIST_ACCOUNT')
        put(db,3,4,state='COMPLETED',assessed=True)
        out=campaign_assessment_operations_overview(db,2)
        assert out['campaign_id']=='2'
        assert out['assessment_link_coverage']['monitoring_evidence_links']==2
        assert out['assessment_link_coverage']['watchlist_account_links_excluded_from_ai']==1
        assert out['assessment_link_coverage']['pending_monitoring_without_job']==1
        assert out['completion_audit']['ordinary_jobs']==1
        assert out['interrupted_recovery']['total_ordinary_jobs']==1
        assert [x['code'] for x in out['issues']]==['UNQUEUED_EVIDENCE']
        assert out['automatic_ai_authorized'] is False
        assert out['paid_provider_called'] is False and out['database_writes']==0
        assert db.query(AIAssessmentJob).count()==2
    finally:db.close();e.dispose()

def test_integrity_and_stale_status_issue_order_is_deterministic(monkeypatch):
    e,db=fixture()
    try:
        from datetime import datetime,timedelta
        put(db,4,1,state='PROCESSING')
        x=db.query(AIAssessmentJob).filter_by(campaign_id=4).one()
        x.updated_at=datetime.utcnow()-timedelta(minutes=15)
        put(db,4,2,state='COMPLETED',assessed=True)
        db.flush()
        out=campaign_assessment_operations_overview(db,4)
        assert out['review_required'] is True
        assert [x['code'] for x in out['issues']]==[
            'STALE_PROCESSING','COMPLETION_PROVENANCE_GAP']
        assert out['interrupted_recovery']['stale_processing_jobs']==1
        assert out['completion_audit']['completed_requiring_manual_history_review']==1
        assert out['automatically_retries_jobs'] is False
    finally:db.close();e.dispose()

def test_dispatch_is_authorized_on_existing_campaign_action():
    from pathlib import Path
    root=Path(__file__).parents[1]/'app'
    c=(root/'campaigns.py').read_text()
    dispatch=(root/'socialcrawl.py').read_text()
    assert "if action=='campaignAssessmentOperationsOverview':" in c
    block=c.split("if action=='campaignAssessmentOperationsOverview':",1)[1].split("if action=='campaignAIWorkerReadiness':",1)[0]
    assert "if not campaign or not allowed(p,campaign)" in block
    assert "campaign_assessment_operations_overview(db,campaign.id)" in block
    assert "'campaignAssessmentOperationsOverview'" in dispatch
