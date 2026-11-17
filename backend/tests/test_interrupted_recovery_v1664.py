"""v166.4: stale worker jobs can be quarantined without replay/billing."""
from datetime import datetime,timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob
from app.assessment_interrupted_recovery import (
    interrupted_campaign_preview,quarantine_interrupted_campaign_jobs)

def fixture():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    return e,Session(e)

def put(db,cid,rid,minutes=20,kind='KEYWORD',state='PROCESSING'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,
        attempts=1,updated_at=datetime.utcnow()-timedelta(minutes=minutes)))
    db.flush()

def test_preview_read_only_and_quarantine_only_older_ordinary_jobs():
    eng,db=fixture()
    try:
        put(db,4,1)
        put(db,4,2,minutes=2)
        put(db,4,3,kind='WATCHLIST_ACCOUNT')
        put(db,5,4)
        put(db,4,5,state='COMPLETED')
        db.commit()
        before=[(x.id,x.state,x.attempts) for x in db.query(AIAssessmentJob).all()]
        preview=interrupted_campaign_preview(db,4)
        assert preview['stale_processing_jobs']==1
        assert preview['paid_provider_called'] is False
        assert preview['database_writes']==0
        assert before==[(x.id,x.state,x.attempts) for x in db.query(AIAssessmentJob).all()]
        result=quarantine_interrupted_campaign_jobs(db,4)
        assert result['quarantined_jobs']==1
        assert result['automatically_retried'] is False
        one=db.query(AIAssessmentJob).filter_by(campaign_id=4,result_id=1).one()
        assert one.state=='FAILED' and one.attempts==1
        assert 'provider call status unknown' in one.last_error
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,result_id=2).one().state=='PROCESSING'
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,result_id=3).one().state=='PROCESSING'
        assert db.query(AIAssessmentJob).filter_by(campaign_id=5,result_id=4).one().state=='PROCESSING'
        assert quarantine_interrupted_campaign_jobs(db,4)['quarantined_jobs']==0
    finally:db.close();eng.dispose()

def test_quarantine_batch_is_bounded_oldest_and_safe_to_repeat():
    eng,db=fixture()
    try:
        for i in range(1,4):put(db,4,i)
        assert quarantine_interrupted_campaign_jobs(db,4,limit=2)['quarantined_jobs']==2
        assert quarantine_interrupted_campaign_jobs(db,4,limit=2)['quarantined_jobs']==1
        assert quarantine_interrupted_campaign_jobs(db,4,limit=2)['quarantined_jobs']==0
        assert db.query(AIAssessmentJob).filter_by(state='FAILED').count()==3
    finally:db.close();eng.dispose()

def test_invalid_limits_and_public_confirm_guard():
    eng,db=fixture()
    try:
        for value in (0,101,True,'5'):
            try:quarantine_interrupted_campaign_jobs(db,4,limit=value)
            except ValueError:pass
            else:assert False,value
        from pathlib import Path
        p=Path(__file__).parents[1]/'app'
        c=(p/'campaigns.py').read_text()
        s=(p/'socialcrawl.py').read_text()
        assert "if not _editable(p,campaign):" in c
        assert "if (data or {}).get('confirm_no_retry_quarantine') is not True:" in c
        assert "'campaignAssessmentInterruptedQuarantine'" in s
        assert "'campaignAssessmentInterruptedPreview'" in s
    finally:db.close();eng.dispose()
