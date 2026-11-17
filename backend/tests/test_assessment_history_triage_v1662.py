"""v166.2: historical assessment provenance gaps remain review-only."""
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit

def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def put(db,cid,rid,attempts=1,state='COMPLETED',kind='KEYWORD',models=('LEGACY_MODEL',),usage=False):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=attempts,
                           created_at=datetime(2026,10,28)))
    for version,model in enumerate(models,1):
        a=EvidenceAssessment(campaign_id=cid,result_id=rid,assessment_version=version,
                             model_version=model,relevance_label='RELEVANT')
        db.add(a);db.flush()
        if usage and version==1:
            db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=cid))
    db.flush()

def test_multi_version_legacy_history_is_not_authorization_to_retry():
    engine,db=fixture()
    try:
        put(db,1,1,models=('INITIAL_MODEL','PRISM_OPENAI_TOPIC_CLASSIFIER'))
        put(db,1,2,models=('INITIAL_MODEL','PRISM_OPENAI_TOPIC_CLASSIFIER'))
        put(db,1,3,attempts=0,models=('OTHER_MODEL',))
        put(db,1,4,models=('INITIAL','LATEST'),usage=True)
        put(db,1,5,state='PENDING',models=('LATEST',))
        put(db,1,6,kind='WATCHLIST_ACCOUNT',models=('LATEST',))
        put(db,2,7,models=('LATEST',))
        before=db.query(AIAssessmentJob).count()
        audit=campaign_completion_audit(db,1)
        history=audit['historical_missing_usage_triage']
        assert audit['completed_jobs']==4
        assert audit['verified_usage_backed_completed_jobs']==1
        assert history['completed_valid_relevance_without_usage']==3
        assert history['with_recorded_attempts']==2
        assert history['with_multiple_assessment_versions']==2
        assert history['earliest_job_created_date']=='2026-10-28'
        assert history['latest_job_created_date']=='2026-10-28'
        assert history['latest_saved_model_distribution']==[
          {'latest_model':'PRISM_OPENAI_TOPIC_CLASSIFIER','jobs':2},
          {'latest_model':'OTHER_MODEL','jobs':1}]
        assert history['cause_of_missing_usage']=='UNDETERMINED'
        assert history['automatic_reprocessing_permitted'] is False
        assert audit['source_text_or_ids_returned'] is False
        assert db.query(AIAssessmentJob).count()==before
    finally:db.close();engine.dispose()

def test_no_gaps_have_explicit_empty_history_and_no_side_effects():
    engine,db=fixture()
    try:
        put(db,2,1,models=('MODEL',),usage=True)
        out=campaign_completion_audit(db,2)
        triage=out['historical_missing_usage_triage']
        assert triage['completed_valid_relevance_without_usage']==0
        assert triage['with_multiple_assessment_versions']==0
        assert triage['earliest_job_created_date'] is None
        assert triage['latest_saved_model_distribution']==[]
        assert triage['manual_provenance_review_required'] is False
        assert out['paid_provider_called'] is False and out['database_writes']==0
    finally:db.close();engine.dispose()
