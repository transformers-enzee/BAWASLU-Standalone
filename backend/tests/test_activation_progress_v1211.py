"""Regression: interrupted AI workers must not silently appear to make progress."""
from datetime import datetime,timedelta
from types import SimpleNamespace
from app.activation_assessment import stale_processing_claim

def test_stale_processing_is_reportable_not_retried():
    now=datetime.utcnow()
    stale=SimpleNamespace(state='PROCESSING',updated_at=now-timedelta(minutes=11))
    healthy=SimpleNamespace(state='PROCESSING',updated_at=now-timedelta(seconds=20))
    pending=SimpleNamespace(state='PENDING',updated_at=now-timedelta(hours=1))
    assert stale_processing_claim(stale,now) is True
    assert stale_processing_claim(healthy,now) is False
    assert stale_processing_claim(pending,now) is False
    assert stale.state=='PROCESSING' # status detection never modifies the database

def test_stale_job_does_not_trigger_implicit_paid_retries():
    from pathlib import Path
    import app.activation_assessment as activation
    src=Path(activation.__file__).read_text()
    assert 'recover_stale_jobs' not in src # only an authorized resume quarantines claims
    assert 'pending_campaign_job_links(db,campaign_id,limit=200,result_ids=chunk)' in src
    assert 'target_result_ids=batch' in src


def test_scoped_batch_excludes_interrupted_and_uncertain_claims():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db import Base
    from app.models import CampaignEvidence,AIAssessmentJob
    from app.assessment_job_reconcile import pending_campaign_job_links,enqueue_scoped_jobs
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    try:
        for rid in range(1,6):
            db.add(CampaignEvidence(campaign_id=91,result_id=rid,match_method='KEYWORD'))
        old=datetime.utcnow()-timedelta(minutes=30)
        for rid,state,attempts in [(1,'PROCESSING',1),(2,'FAILED',1),(3,'PENDING',3),(4,'PENDING',0),(5,'PENDING',0)]:
            db.add(AIAssessmentJob(campaign_id=91,result_id=rid,state=state,attempts=attempts,updated_at=old))
        db.commit()
        assert enqueue_scoped_jobs(db,91,[1,2,3,4])==0
        assert [row.result_id for row in pending_campaign_job_links(db,91,result_ids=[1,2,3,4])]==[4]
        assert [(j.state,j.attempts) for j in db.query(AIAssessmentJob).order_by(AIAssessmentJob.result_id).all()]==[
            ('PROCESSING',1),('FAILED',1),('PENDING',3),('PENDING',0),('PENDING',0)]
    finally:db.close();engine.dispose()

