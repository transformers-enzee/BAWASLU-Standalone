"""v167.7 classification usage lineage must match job state without mutation."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit
from app.assessment_operations_overview import campaign_assessment_operations_overview

def fixture():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    return e,Session(e)

def put(db,cid,rid,state='COMPLETED',usage_count=1,kind='RELEVANCE_AND_CLASSIFICATION'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method='KEYWORD'))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=1))
    a=EvidenceAssessment(campaign_id=cid,result_id=rid,assessment_version=1,relevance_label='RELEVANT')
    db.add(a);db.flush()
    for _ in range(usage_count):
        db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=cid,provider_model='test',
            request_kind=kind,input_tokens=4,output_tokens=2,usage_reported=True))
    db.flush()

def test_detects_noncompleted_classification_usage_and_duplicate_rows():
    e,db=fixture()
    try:
        put(db,4,1,state='PROCESSING')
        put(db,4,2,state='PENDING')
        put(db,4,3,state='COMPLETED')
        put(db,4,4,state='FAILED',kind='STANDALONE_SENTIMENT')
        put(db,5,5,state='COMPLETED')
        out=campaign_completion_audit(db,4)
        x=out['classification_usage_lifecycle_quality']
        assert x['noncompleted_jobs_with_classification_usage']==2
        assert x['assessments_with_duplicate_classification_usage']==0
        assert x['requires_manual_review'] is True
        assert x['automatic_job_state_reconciliation'] is False
        assert x['automatic_usage_deduplication'] is False
        assert out['verified_usage_backed_completed_jobs']==1
        ov=campaign_assessment_operations_overview(db,4)
        assert 'CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT' in [i['code'] for i in ov['issues']]
        assert ov['database_writes']==0 and not ov['paid_provider_called']
        assert db.query(AssessmentAIUsage).count()==5
    finally:db.close();e.dispose()

def test_ordinary_completed_and_separate_campaign_no_warning():
    e,db=fixture()
    try:
        put(db,2,1,state='COMPLETED')
        put(db,3,2,state='PROCESSING')
        out=campaign_completion_audit(db,2)
        x=out['classification_usage_lifecycle_quality']
        assert x['noncompleted_jobs_with_classification_usage']==0
        assert x['assessments_with_duplicate_classification_usage']==0
        assert not x['requires_manual_review']
    finally:db.close();e.dispose()

def test_database_rejects_duplicate_usage_per_assessment():
    import pytest
    from sqlalchemy.exc import IntegrityError
    e,db=fixture()
    try:
        put(db,4,1,state='COMPLETED')
        a=db.query(EvidenceAssessment).one()
        db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=4,provider_model='test',
            request_kind='RELEVANCE_AND_CLASSIFICATION',input_tokens=1,output_tokens=1,
            usage_reported=True))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.query(AssessmentAIUsage).count()==1
    finally:db.close();e.dispose()
