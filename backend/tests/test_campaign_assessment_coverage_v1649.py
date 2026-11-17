"""Campaign link assessment coverage: watchlist is not unpaid AI backlog."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,EvidenceAssessment,AIAssessmentJob
from app.campaign_assessment_coverage import campaign_link_assessment_coverage

def build():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def seed(db,cid,rid,method='KEYWORD',label=None,job=None,version=1):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    if label is not None:
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
            assessment_version=version,relevance_label=label))
    if job:
        db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=job))
    db.flush()

def test_watchlist_without_assessment_does_not_create_ai_backlog():
    eng,db=build()
    try:
        seed(db,1,1,'WATCHLIST_ACCOUNT')
        seed(db,1,2,'WATCHLIST_ACCOUNT')
        seed(db,1,3,'KEYWORD','RELEVANT')
        c=campaign_link_assessment_coverage(db,1)
        assert c['total_campaign_links']==3
        assert c['watchlist_account_links_excluded_from_ai']==2
        assert c['monitoring_evidence_links']==1
        assert c['pending_monitoring_links']==0
        assert c['link_count_reconciled']
        assert not c['ready_for_no_cost_job_reconciliation']
    finally:db.close();eng.dispose()

def test_saved_unassessed_rows_are_pending_even_if_assessment_exists():
    eng,db=build()
    try:
        seed(db,2,1,'KEYWORD','UNASSESSED')
        seed(db,2,2,'KEYWORD',None)
        seed(db,2,3,'PRISM_DISCOVER','RELEVANT')
        out=campaign_link_assessment_coverage(db,2)
        assert out['pending_monitoring_links']==2
        assert out['pending_monitoring_without_job']==2
        assert out['assessed_monitoring_links']==1
        assert out['ready_for_no_cost_job_reconciliation']
        assert out['assessment_rows_labelled_unassessed_remain_pending']
        assert out['database_writes']==0 and not out['paid_provider_called']
    finally:db.close();eng.dispose()

def test_job_states_and_failed_jobs_are_not_silent():
    eng,db=build()
    try:
        seed(db,3,1,'KEYWORD','UNASSESSED',job='FAILED')
        seed(db,3,2,'KEYWORD','UNASSESSED',job='PENDING')
        seed(db,3,3,'KEYWORD',None,job='PROCESSING')
        out=campaign_link_assessment_coverage(db,3)
        assert out['pending_monitoring_links']==3
        assert out['pending_monitoring_without_job']==0
        assert out['pending_monitoring_with_job']==3
        assert out['pending_monitoring_failed_jobs']==1
        assert out['link_count_reconciled']
    finally:db.close();eng.dispose()

def test_only_latest_saved_assessment_version_decides_pending():
    eng,db=build()
    try:
        seed(db,4,1,'KEYWORD','UNASSESSED',version=1)
        db.add(EvidenceAssessment(campaign_id=4,result_id=1,
            assessment_version=2,relevance_label='RELEVANT'))
        seed(db,4,2,'KEYWORD','RELEVANT',version=1)
        db.add(EvidenceAssessment(campaign_id=4,result_id=2,
            assessment_version=2,relevance_label='UNASSESSED'))
        db.flush()
        result=campaign_link_assessment_coverage(db,4)
        assert result['assessed_monitoring_links']==1
        assert result['pending_monitoring_links']==1
        assert result['pending_monitoring_without_job']==1
    finally:db.close();eng.dispose()

def test_authorized_campaign_id_filters_every_aggregate():
    eng,db=build()
    try:
        seed(db,10,1,'WATCHLIST_ACCOUNT')
        seed(db,11,2,'KEYWORD','UNASSESSED')
        a=campaign_link_assessment_coverage(db,10)
        b=campaign_link_assessment_coverage(db,11)
        assert a['watchlist_account_links_excluded_from_ai']==1
        assert a['pending_monitoring_links']==0
        assert b['watchlist_account_links_excluded_from_ai']==0
        assert b['pending_monitoring_links']==1
        assert a['source_text_or_ids_returned'] is False
    finally:db.close();eng.dispose()

def test_empty_campaign_returns_consistent_zeros():
    eng,db=build()
    try:
        out=campaign_link_assessment_coverage(db,500)
        assert out['link_count_reconciled']
        assert out['total_campaign_links']==0
        assert out['pending_monitoring_links']==0
    finally:db.close();eng.dispose()
