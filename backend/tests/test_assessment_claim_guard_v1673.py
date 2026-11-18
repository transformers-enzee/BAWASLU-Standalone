"""v167.3 prevent already-classified PENDING jobs entering a billable claim."""
from sqlalchemy import create_engine,update
from sqlalchemy.orm import Session
from app.db import Base
from app.models import AIAssessmentJob,EvidenceAssessment
from app.assessment_claim_guard import no_latest_relevance_classification

def fixture():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    return e,Session(e)

def make(db,rid,labels=None,state='PENDING'):
    j=AIAssessmentJob(campaign_id=4,result_id=rid,state=state,attempts=0)
    db.add(j)
    for version,label in enumerate(labels or [],1):
        db.add(EvidenceAssessment(campaign_id=4,result_id=rid,
                                  assessment_version=version,relevance_label=label))
    db.flush()
    return j

def claim(db,job):
    result=db.execute(update(AIAssessmentJob).where(
        AIAssessmentJob.id==job.id,
        AIAssessmentJob.state=='PENDING',
        AIAssessmentJob.attempts<3,
        no_latest_relevance_classification(db)).values(
            state='PROCESSING',attempts=AIAssessmentJob.attempts+1))
    db.flush()
    return result.rowcount

def test_latest_relevance_label_blocks_claim_even_after_initial_preview():
    e,db=fixture()
    try:
        a=make(db,1)
        assert claim(db,a)==1
        db.query(AIAssessmentJob).filter_by(id=a.id).update({'state':'PENDING','attempts':0})
        db.add(EvidenceAssessment(campaign_id=4,result_id=1,
            assessment_version=1,relevance_label='RELEVANT'))
        db.flush()
        assert claim(db,a)==0
        assert db.get(AIAssessmentJob,a.id).attempts==0
        assert db.get(AIAssessmentJob,a.id).state=='PENDING'
    finally:db.close();e.dispose()

def test_only_latest_label_counts_and_campaign_scope_is_preserved():
    e,db=fixture()
    try:
        old_valid=make(db,2,['RELEVANT','UNASSESSED'])
        new_valid=make(db,3,['UNASSESSED','UNCERTAIN'])
        missing=make(db,4)
        superseded=make(db,5,['RELEVANT'],state='SUPERSEDED_ASSESSED')
        assert claim(db,old_valid)==1
        assert claim(db,new_valid)==0
        assert claim(db,missing)==1
        assert claim(db,superseded)==0
    finally:db.close();e.dispose()

def test_worker_requires_latest_classification_guard_before_quota_reservation():
    from pathlib import Path
    code=(Path(__file__).parents[1]/'app'/'auto_relevance.py').read_text()
    start=code.index('def _assess_pending_campaign_locked(')
    end=code.index('\ndef assess_pending_campaign(',start)
    worker=code[start:end]
    assert 'no_latest_relevance_classification(db)' in worker
    assert 'if (not reanalysis and already_relevant)' in worker
    assert worker.index('no_latest_relevance_classification(db)') < worker.index('reserve_automatic_ai_request(db,campaign.id)')
    assert worker.index('reserve_automatic_ai_request(db,campaign.id)') < worker.index('response=httpx.post(')
