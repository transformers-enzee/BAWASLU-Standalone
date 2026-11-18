"""v167.4: completion lineage and current classification are independent facts."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit
from app.assessment_operations_overview import campaign_assessment_operations_overview

def setup():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    return e,Session(e)

def add(db,cid,rid,labels,usage_version=None,state='COMPLETED'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method='KEYWORD'))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=1))
    for version,label in enumerate(labels,1):
        a=EvidenceAssessment(campaign_id=cid,result_id=rid,
                             assessment_version=version,relevance_label=label)
        db.add(a);db.flush()
        if usage_version==version:
            db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=cid,
                provider_model='test-model',request_kind='RELEVANCE_AND_CLASSIFICATION',
                input_tokens=7,output_tokens=2,usage_reported=True))
    db.flush()

def test_historical_provider_usage_survives_later_unassessed_version():
    e,db=setup()
    try:
        add(db,2,1,['RELEVANT','UNASSESSED'],usage_version=1)
        add(db,2,2,['RELEVANT','IRRELEVANT'],usage_version=1)
        add(db,2,3,['UNASSESSED'],usage_version=None)
        add(db,3,4,['RELEVANT'],usage_version=1)
        out=campaign_completion_audit(db,2)
        assert out['completed_jobs']==3
        assert out['verified_usage_backed_completed_jobs']==2
        r=out['latest_completion_classification_review']
        assert r['completed_latest_unclassified_or_invalid']==2
        assert r['completed_missing_latest_assessment']==0
        assert r['historically_usage_verified_but_latest_invalid']==1
        assert r['requires_manual_review'] is True
        assert r['does_not_invalidate_historical_usage']
        assert r['automatic_reassessment_permitted'] is False
        summary=campaign_assessment_operations_overview(db,2)
        codes=[x['code'] for x in summary['issues']]
        assert 'COMPLETED_LATEST_CLASSIFICATION_REVIEW' in codes
        assert summary['paid_provider_called'] is False
        assert db.query(AssessmentAIUsage).count()==3
    finally:db.close();e.dispose()

def test_completed_missing_assessment_distinguished_from_no_usage():
    e,db=setup()
    try:
        add(db,5,1,[],usage_version=None)
        out=campaign_completion_audit(db,5)
        r=out['latest_completion_classification_review']
        assert r['completed_missing_latest_assessment']==1
        assert r['completed_latest_unclassified_or_invalid']==0
        assert out['completed_missing_any_assessment']==1
        assert out['verified_usage_backed_completed_jobs']==0
    finally:db.close();e.dispose()
