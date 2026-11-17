"""v165.1: durable worker selection is independent of the latest 300 links."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence, AIAssessmentJob
from app.assessment_job_reconcile import pending_campaign_job_links

def _setup():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def _link(db,campaign,result,method="KEYWORD",state=None,attempts=0):
    db.add(CampaignEvidence(campaign_id=campaign,result_id=result,match_method=method))
    if state:
        db.add(AIAssessmentJob(campaign_id=campaign,result_id=result,
                              state=state,attempts=attempts))
    db.flush()

def test_old_pending_jobs_outside_latest_300_remain_selectable():
    engine,db=_setup()
    try:
        _link(db,2,1,state="PENDING")
        for rid in range(2,307):
            _link(db,2,rid)
        selected=pending_campaign_job_links(db,2)
        assert [link.result_id for link in selected]==[1]
    finally:
        db.close();engine.dispose()

def test_only_claimable_ordinary_campaign_jobs():
    engine,db=_setup()
    try:
        _link(db,2,1,state="COMPLETED")
        _link(db,2,2,state="FAILED")
        _link(db,2,3,state="PROCESSING")
        _link(db,2,4,state="PENDING",attempts=3)
        _link(db,2,5,method="WATCHLIST_ACCOUNT",state="PENDING")
        _link(db,3,6,state="PENDING")
        _link(db,2,7,state="PENDING")
        _link(db,2,8)
        assert [link.result_id for link in pending_campaign_job_links(db,2)]==[7]
        assert [link.result_id for link in pending_campaign_job_links(db,3)]==[6]
    finally:
        db.close();engine.dispose()

def test_queue_selection_oldest_first_bounded_and_read_only():
    engine,db=_setup()
    try:
        for rid in (11,12,13,14):
            _link(db,4,rid,state="PENDING")
        assert [x.result_id for x in pending_campaign_job_links(db,4,limit=2)]==[11,12]
        assert [x.result_id for x in pending_campaign_job_links(db,4,limit=2)]==[11,12]
        assert db.query(AIAssessmentJob).filter(AIAssessmentJob.state=="PENDING").count()==4
    finally:
        db.close();engine.dispose()

def test_invalid_limits_rejected_without_writes():
    engine,db=_setup()
    try:
        for limit in (0,201,True,1.5,"5",-1):
            try:
                pending_campaign_job_links(db,2,limit=limit)
            except ValueError:
                pass
            else:
                assert False,limit
        assert db.query(AIAssessmentJob).count()==0
    finally:
        db.close();engine.dispose()
