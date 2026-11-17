"""No-cost, exactly-once campaign assessment job reconciliation in SQLite."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,EvidenceAssessment,AIAssessmentJob
from app.assessment_job_reconcile import enqueue_unassessed_campaign_jobs

def fixture():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def link(db,cid,rid,method="KEYWORD",labels=(),job=None):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    for n,label in enumerate(labels,1):
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
            assessment_version=n,relevance_label=label))
    if job:
        db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=job,
            attempts=2 if job=="FAILED" else 0))
    db.flush()

def test_enqueue_ordinary_unassessed_only_and_is_idempotent():
    engine,db=fixture()
    try:
        link(db,1,1,"WATCHLIST_ACCOUNT")
        link(db,1,2,"KEYWORD",("UNASSESSED",))
        link(db,1,3,"KEYWORD",())
        link(db,1,4,"PRISM_DISCOVER",("RELEVANT",))
        link(db,1,5,"KEYWORD",("UNASSESSED","IRRELEVANT"))
        link(db,1,6,"KEYWORD",("RELEVANT","UNASSESSED"))
        assert enqueue_unassessed_campaign_jobs(db,1)==3
        assert enqueue_unassessed_campaign_jobs(db,1)==0
        rows=db.query(AIAssessmentJob).order_by(AIAssessmentJob.result_id).all()
        assert [(r.result_id,r.state,r.attempts) for r in rows]==[
            (2,"PENDING",0),(3,"PENDING",0),(6,"PENDING",0)]
    finally:db.close();engine.dispose()

def test_failed_completed_and_processing_jobs_never_automatically_requeued():
    engine,db=fixture()
    try:
        link(db,1,1,labels=("UNASSESSED",),job="FAILED")
        link(db,1,2,labels=("UNASSESSED",),job="COMPLETED")
        link(db,1,3,labels=("UNASSESSED",),job="PROCESSING")
        assert enqueue_unassessed_campaign_jobs(db,1)==0
        assert sorted(r.state for r in db.query(AIAssessmentJob).all())==[
            "COMPLETED","FAILED","PROCESSING"]
    finally:db.close();engine.dispose()

def test_older_first_bounded_batch_and_repeat_advances():
    engine,db=fixture()
    try:
        for rid in range(1,6):link(db,3,rid,labels=("UNASSESSED",))
        assert enqueue_unassessed_campaign_jobs(db,3,limit=2)==2
        assert sorted(r.result_id for r in db.query(AIAssessmentJob).all())==[1,2]
        assert enqueue_unassessed_campaign_jobs(db,3,limit=2)==2
        assert enqueue_unassessed_campaign_jobs(db,3,limit=2)==1
        assert enqueue_unassessed_campaign_jobs(db,3,limit=2)==0
    finally:db.close();engine.dispose()

def test_other_campaign_work_never_enqueued():
    engine,db=fixture()
    try:
        link(db,1,1,labels=("UNASSESSED",))
        link(db,2,2,labels=("UNASSESSED",))
        assert enqueue_unassessed_campaign_jobs(db,1)==1
        assert [(x.campaign_id,x.result_id) for x in db.query(AIAssessmentJob).all()]==[(1,1)]
    finally:db.close();engine.dispose()

def test_max_batch_safety_and_invalid_values():
    engine,db=fixture()
    try:
        for value in (0,201,True,1.5,"2",-1):
            try:enqueue_unassessed_campaign_jobs(db,1,limit=value)
            except ValueError:pass
            else:assert False,value
        assert db.query(AIAssessmentJob).count()==0
    finally:db.close();engine.dispose()

def test_no_provider_network_activity_or_assessment_mutation():
    engine,db=fixture()
    try:
        link(db,9,4,labels=("UNASSESSED",))
        before=[(a.id,a.relevance_label,a.assessment_version)
                for a in db.query(EvidenceAssessment).all()]
        assert enqueue_unassessed_campaign_jobs(db,9)==1
        assert before==[(a.id,a.relevance_label,a.assessment_version)
                        for a in db.query(EvidenceAssessment).all()]
    finally:db.close();engine.dispose()

def test_new_pending_jobs_populate_required_fields_without_server_defaults():
    engine,db=fixture()
    try:
        link(db,12,4242,labels=("UNASSESSED",))
        assert enqueue_unassessed_campaign_jobs(db,12)==1
        job=db.query(AIAssessmentJob).filter_by(campaign_id=12,result_id=4242).one()
        assert job.state=="PENDING" and job.attempts==0
        assert job.last_error==""
        assert job.created_at is not None and job.updated_at is not None
        assert enqueue_unassessed_campaign_jobs(db,12)==0
    finally:db.close();engine.dispose()
