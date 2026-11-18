"""v167.5 request-kind provenance for completed relevance jobs."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit
from app.assessment_operations_overview import campaign_assessment_operations_overview
def fixture():
    e=create_engine('sqlite:///:memory:');Base.metadata.create_all(e);return e,Session(e)
def add(db,cid,rid,kind=None):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method='KEYWORD'))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state='COMPLETED',attempts=1))
    a=EvidenceAssessment(campaign_id=cid,result_id=rid,assessment_version=1,relevance_label='RELEVANT')
    db.add(a);db.flush()
    if kind:db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=cid,provider_model='test',
        request_kind=kind,input_tokens=3,output_tokens=2,usage_reported=True))
    db.flush()
def test_sentiment_usage_does_not_verify_relevance_completion():
    e,db=fixture()
    try:
        add(db,4,1,'STANDALONE_SENTIMENT')
        add(db,4,2,'RELEVANCE_AND_CLASSIFICATION')
        add(db,4,3)
        add(db,5,4,'RELEVANCE_AND_CLASSIFICATION')
        out=campaign_completion_audit(db,4)
        assert out['completed_jobs']==3
        assert out['verified_usage_backed_completed_jobs']==1
        assert out['completed_sentiment_usage_without_classification_usage']==1
        assert out['completed_valid_relevance_missing_linked_usage']==2
        assert out['completed_requiring_manual_history_review']==2
        assert out['classification_usage_request_kind_required']
        assert 'SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF' in [x['code'] for x in campaign_assessment_operations_overview(db,4)['issues']]
        assert db.query(AssessmentAIUsage).count()==3
    finally:db.close();e.dispose()
def test_later_sentiment_version_does_not_erase_earlier_classification():
    e,db=fixture()
    try:
        add(db,3,1,'RELEVANCE_AND_CLASSIFICATION')
        a=EvidenceAssessment(campaign_id=3,result_id=1,assessment_version=2,relevance_label='RELEVANT')
        db.add(a);db.flush()
        db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=3,provider_model='test',
            request_kind='STANDALONE_SENTIMENT',input_tokens=3,output_tokens=2,usage_reported=True))
        db.flush()
        out=campaign_completion_audit(db,3)
        assert out['verified_usage_backed_completed_jobs']==1
        assert out['completed_sentiment_usage_without_classification_usage']==0
    finally:db.close();e.dispose()
