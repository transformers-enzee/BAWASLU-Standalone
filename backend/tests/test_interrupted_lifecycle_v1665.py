"""v166.5 lifecycle reconciliation of confirmed interrupted-job quarantine."""
from datetime import datetime,timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import AIAssessmentJob,CampaignEvidence
from app.assessment_interrupted_recovery import (
    interrupted_campaign_preview,quarantine_interrupted_campaign_jobs,
    _REASON,_stale_query)

def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def seed(db,cid,rid,state='PROCESSING',age=20,kind='KEYWORD',reason=''):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,
        last_error=reason,attempts=1,
        updated_at=datetime.utcnow()-timedelta(minutes=age)))
    db.flush()

def test_reconcile_preview_before_and_after_quarantine():
    engine,db=fixture()
    try:
        seed(db,4,1)
        seed(db,4,2)
        seed(db,4,3,age=1)
        seed(db,4,4,state='FAILED',reason=_REASON)
        seed(db,4,5,state='FAILED',reason='Other provider error')
        seed(db,4,6,state='PENDING')
        seed(db,4,7,state='COMPLETED')
        seed(db,4,8,kind='WATCHLIST_ACCOUNT')
        seed(db,5,9)
        initial=interrupted_campaign_preview(db,4)
        assert initial['stale_processing_jobs']==2
        assert initial['processing_not_stale']==1
        assert initial['already_quarantined_for_manual_review']==1
        assert initial['other_failed_jobs']==1
        assert initial['pending_jobs']==1
        assert initial['completed_jobs']==1
        assert initial['total_ordinary_jobs']==7
        result=quarantine_interrupted_campaign_jobs(db,4,limit=1)
        assert result['quarantined_jobs']==1
        assert result['remaining_stale_jobs']==1
        later=interrupted_campaign_preview(db,4)
        assert later['stale_processing_jobs']==1
        assert later['already_quarantined_for_manual_review']==2
        assert later['processing_not_stale']==1
        assert later['pending_jobs']==1
        result=quarantine_interrupted_campaign_jobs(db,4,limit=1)
        assert result['quarantined_jobs']==1
        assert result['remaining_stale_jobs']==0
        assert interrupted_campaign_preview(db,4)['already_quarantined_for_manual_review']==3
        assert quarantine_interrupted_campaign_jobs(db,4)['quarantined_jobs']==0
        assert db.query(AIAssessmentJob).filter_by(campaign_id=5).one().state=='PROCESSING'
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,result_id=8).one().state=='PROCESSING'
    finally:db.close();engine.dispose()

def test_cas_guard_rechecks_watchlist_match_at_write_time():
    from pathlib import Path
    code=(Path(__file__).parents[1]/'app'/'assessment_interrupted_recovery.py').read_text()
    block=code.split('stmt=(update(AIAssessmentJob)',1)[1].split('try:',1)[0]
    assert "CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'" in block
    assert "AIAssessmentJob.state=='PROCESSING'" in block
    assert "AIAssessmentJob.updated_at<cutoff" in block
