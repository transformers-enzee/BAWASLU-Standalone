"""v166.1 read-only completed-job assessment and usage lineage verification."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit

def setup():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def job(db,cid,rid,state='COMPLETED',kind='KEYWORD',attempts=1):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=attempts))
    db.flush()

def assess(db,cid,rid,version,label,usage=False,usage_campaign=None):
    a=EvidenceAssessment(campaign_id=cid,result_id=rid,
                         assessment_version=version,relevance_label=label)
    db.add(a);db.flush()
    if usage:db.add(AssessmentAIUsage(
        assessment_id=a.id,campaign_id=cid if usage_campaign is None else usage_campaign,
        provider_model='test-model',request_kind='RELEVANCE_AND_CLASSIFICATION'))
    db.flush()
    return a

def test_verifies_provenance_not_just_any_assessment():
    eng,db=setup()
    try:
        job(db,2,1);assess(db,2,1,1,'RELEVANT',usage=True)
        # A later review/sentiment update must not hide original usage.
        assess(db,2,1,2,'RELEVANT')
        job(db,2,2);assess(db,2,2,1,'IRRELEVANT')
        job(db,2,3);assess(db,2,3,1,'UNASSESSED',usage=True)
        job(db,2,4)
        job(db,2,5);assess(db,2,5,1,'UNCERTAIN',usage=True)
        job(db,2,6,state='PENDING')
        job(db,2,7,state='PROCESSING')
        job(db,2,8,state='FAILED')
        out=campaign_completion_audit(db,2)
        assert out['ordinary_jobs']==8
        assert out['completed_jobs']==5
        assert out['verified_usage_backed_completed_jobs']==2
        assert out['completed_missing_any_assessment']==1
        assert out['completed_without_valid_relevance']==1
        assert out['completed_valid_relevance_missing_linked_usage']==1
        assert out['completed_usage_without_valid_relevance']==1
        assert out['completed_requiring_manual_history_review']==3
        assert out['pending_jobs']==out['processing_jobs']==out['failed_jobs']==1
        assert out['counts_reconciled'] and not out['completion_reconciled']
        assert out['paid_provider_called'] is False and out['database_writes']==0
    finally:db.close();eng.dispose()

def test_wrong_campaign_usage_cannot_verify_completion():
    eng,db=setup()
    try:
        job(db,2,2);assess(db,2,2,1,'RELEVANT',usage=True,usage_campaign=3)
        out=campaign_completion_audit(db,2)
        assert out['verified_usage_backed_completed_jobs']==0
        assert out['completed_valid_relevance_missing_linked_usage']==1
    finally:db.close();eng.dispose()

def test_watchlist_and_other_campaign_isolation_and_no_auto_retry():
    eng,db=setup()
    try:
        job(db,2,1,kind='WATCHLIST_ACCOUNT')
        job(db,3,2)
        job(db,2,3,state='PENDING')
        out=campaign_completion_audit(db,2)
        assert out['ordinary_jobs']==out['pending_jobs']==1
        assert out['completed_jobs']==0 and out['completion_reconciled']
        assert out['automatically_retry_missing_usage'] is False
        assert out['source_text_or_ids_returned'] is False
        assert db.query(AIAssessmentJob).count()==3
    finally:db.close();eng.dispose()

def test_public_dispatch_is_campaign_authorized_and_read_only():
    from pathlib import Path
    root=Path(__file__).parents[1]/'app'
    c=(root/'campaigns.py').read_text()
    social=(root/'socialcrawl.py').read_text()
    assert "'campaignAssessmentCompletionAudit'" in social
    assert "if action=='campaignAssessmentCompletionAudit':" in c
    assert "if not campaign or not allowed(p,campaign):raise ValueError('Campaign not available')" in c
    assert 'return campaign_completion_audit(db,campaign.id)' in c
