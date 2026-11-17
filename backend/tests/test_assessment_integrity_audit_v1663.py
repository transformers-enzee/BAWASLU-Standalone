"""v166.3: source-linked usage integrity and stale-processing quarantine readiness."""
from datetime import datetime,timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit

def setup():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def add(db,cid,rid,state='COMPLETED',kind='KEYWORD',updated=None):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=1,
                           updated_at=updated or datetime.utcnow()))
    db.flush()

def assessment(db,cid,rid,usage_campaign=None,reported=True,inputs=1,outputs=1,model='model'):
    a=EvidenceAssessment(campaign_id=cid,result_id=rid,
                         assessment_version=1,relevance_label='RELEVANT')
    db.add(a);db.flush()
    db.add(AssessmentAIUsage(assessment_id=a.id,
        campaign_id=cid if usage_campaign is None else usage_campaign,
        input_tokens=inputs,output_tokens=outputs,provider_model=model,
        usage_reported=reported,request_kind='RELEVANCE_AND_CLASSIFICATION'))
    db.flush()

def test_usage_checks_are_campaign_scoped_and_read_only():
    engine,db=setup()
    try:
        add(db,2,1);assessment(db,2,1)
        add(db,2,2);assessment(db,2,2,usage_campaign=3,
                               reported=False,inputs=-2,model='')
        add(db,3,3);assessment(db,3,3)
        out=campaign_completion_audit(db,2)
        quality=out['usage_lineage_quality']
        assert quality['assessment_linked_usage_rows']==2
        assert quality['campaign_id_mismatch']==1
        assert quality['provider_usage_not_reported']==1
        assert quality['negative_token_counts']==1
        assert quality['provider_model_missing']==1
        assert not quality['quality_checks_passed']
        assert out['verified_usage_backed_completed_jobs']==1
        assert quality['usage_records_repaired']==0
        assert out['paid_provider_called'] is False and out['database_writes']==0
    finally:db.close();engine.dispose()

def test_stale_processing_identified_without_retry_or_mutation():
    engine,db=setup()
    try:
        old=datetime.utcnow()-timedelta(minutes=12)
        fresh=datetime.utcnow()-timedelta(minutes=1)
        add(db,4,1,state='PROCESSING',updated=old)
        add(db,4,2,state='PROCESSING',updated=fresh)
        add(db,4,3,state='PROCESSING',kind='WATCHLIST_ACCOUNT',updated=old)
        add(db,5,4,state='PROCESSING',updated=old)
        before=[(j.id,j.state,j.attempts) for j in db.query(AIAssessmentJob).all()]
        out=campaign_completion_audit(db,4)
        assert out['processing_jobs']==2
        assert out['stale_processing_jobs']==1
        assert out['stale_processing_requires_history_review'] is True
        assert out['stale_processing_automatically_retried'] is False
        assert before==[(j.id,j.state,j.attempts) for j in db.query(AIAssessmentJob).all()]
    finally:db.close();engine.dispose()

def test_no_processing_or_usage_returns_clear_zeros():
    engine,db=setup()
    try:
        out=campaign_completion_audit(db,9)
        assert out['stale_processing_jobs']==0
        assert out['usage_lineage_quality']['assessment_linked_usage_rows']==0
        assert out['usage_lineage_quality']['quality_checks_passed'] is True
    finally:db.close();engine.dispose()
