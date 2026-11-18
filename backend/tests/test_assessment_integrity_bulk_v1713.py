"""v171.3: completion normalization and nonadditive provider-usage diagnostics."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit
from app.assessment_queue_triage import assessment_queue_triage

def readiness():
    return {'queue_counts':{'claimable_pending_with_text':0,
        'pending_missing_source_or_text':0,'pending_attempts_exhausted':0},
        'pending_already_assessed_excluded_from_ai':0}

def recovery(completed):
    return {'total_ordinary_jobs':completed,'completed_jobs':completed,
        'processing_not_stale':0,'stale_processing_jobs':0,'pending_jobs':0,
        'other_failed_jobs':0,'already_quarantined_for_manual_review':0,
        'superseded_assessed_jobs':0}

def test_completion_case_and_whitespace_normalization_with_usage_kind_guards():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    try:
        for rid,label,kind in [(1,' HIGHLY_RELEVANT  ','RELEVANCE_AND_CLASSIFICATION'),
                               (2,' relevant ','STANDALONE_SENTIMENT'),
                               (3,' unknown ','RELEVANCE_AND_CLASSIFICATION')]:
            db.add(CampaignEvidence(campaign_id=91,result_id=rid,match_method='KEYWORD'))
            db.add(AIAssessmentJob(campaign_id=91,result_id=rid,state='COMPLETED',attempts=1))
            a=EvidenceAssessment(campaign_id=91,result_id=rid,
                assessment_version=1,relevance_label=label)
            db.add(a);db.flush()
            db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=91,
                provider_model='synthetic',request_kind=kind))
        db.flush()
        result=campaign_completion_audit(db,91)
        assert result['completed_jobs']==3
        assert result['verified_usage_backed_completed_jobs']==1
        assert result['completed_without_valid_relevance']==1
        assert result['completed_sentiment_usage_without_classification_usage']==1
        assert result['latest_completion_classification_review']['completed_latest_unclassified_or_invalid']==1
        assert result['database_writes']==0 and not result['paid_provider_called']
    finally:db.close();engine.dispose()

def test_integrity_flags_hold_history_without_double_counting_jobs():
    audit={'completed_jobs':2,'verified_usage_backed_completed_jobs':2,
           'completed_requiring_manual_history_review':0,
           'usage_lineage_quality':{'assessment_linked_usage_rows':4,
              'campaign_id_mismatch':1,'provider_usage_not_reported':2,
              'negative_token_counts':1,'provider_model_missing':1},
           'classification_usage_lifecycle_quality':{
              'noncompleted_jobs_with_classification_usage':1,
              'assessments_with_duplicate_classification_usage':1}}
    result=assessment_queue_triage(readiness(),recovery(2),{},audit)
    integrity=result['provider_usage_integrity']
    assert result['status']=='HOLD_FOR_HISTORY_REVIEW'
    assert integrity['status']=='REVIEW_REQUIRED'
    assert integrity['usage_rows']==4
    assert integrity['flag_counts_may_overlap'] is True
    assert integrity['usage_flags']['provider_usage_not_reported']==2
    assert integrity['lifecycle_flags']['assessments_with_duplicate_classification_usage']==1
    assert result['ordinary_job_total']==result['bucket_total']==2
    assert not integrity['automatic_retry_permitted']
    assert result['database_writes']==0 and not result['paid_provider_called']

def test_clean_and_missing_audit_are_not_conflated():
    clean={'completed_jobs':0,'verified_usage_backed_completed_jobs':0,
           'completed_requiring_manual_history_review':0,
           'usage_lineage_quality':{'assessment_linked_usage_rows':0},
           'classification_usage_lifecycle_quality':{}}
    result=assessment_queue_triage(readiness(),recovery(0),{},clean)
    assert result['provider_usage_integrity']['status']=='NO_RECORDED_ISSUES'
    missing=assessment_queue_triage(readiness(),recovery(0),{},{
         'completed_jobs':0,'verified_usage_backed_completed_jobs':0,
         'completed_requiring_manual_history_review':0})
    assert missing['provider_usage_integrity']['status']=='AUDIT_UNAVAILABLE'
    assert missing['paid_provider_called'] is False
