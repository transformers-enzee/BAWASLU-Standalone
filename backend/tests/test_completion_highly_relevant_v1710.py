"""v171.0: HIGHLY_RELEVANT completion requires classification usage lineage."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,AssessmentAIUsage
from app.assessment_completion_audit import campaign_completion_audit

def test_highly_relevant_is_valid_only_with_linked_classification_usage():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db=Session(engine)
    try:
        for rid, usage_kind in [(1,"RELEVANCE_AND_CLASSIFICATION"),(2,None),
                                (3,"STANDALONE_SENTIMENT")]:
            db.add(CampaignEvidence(campaign_id=81,result_id=rid,match_method="KEYWORD"))
            db.add(AIAssessmentJob(campaign_id=81,result_id=rid,state="COMPLETED",attempts=1))
            a=EvidenceAssessment(campaign_id=81,result_id=rid,
                                 assessment_version=1,relevance_label="HIGHLY_RELEVANT")
            db.add(a)
            db.flush()
            if usage_kind:
                db.add(AssessmentAIUsage(assessment_id=a.id,campaign_id=81,
                    provider_model="synthetic",request_kind=usage_kind))
        # Neither watchlist-only nor another campaign may be counted.
        db.add(CampaignEvidence(campaign_id=81,result_id=4,match_method="WATCHLIST_ACCOUNT"))
        db.add(AIAssessmentJob(campaign_id=81,result_id=4,state="COMPLETED",attempts=1))
        db.add(CampaignEvidence(campaign_id=82,result_id=5,match_method="KEYWORD"))
        db.add(AIAssessmentJob(campaign_id=82,result_id=5,state="COMPLETED",attempts=1))
        db.flush()
        before=[(j.id,j.state,j.attempts) for j in db.query(AIAssessmentJob).order_by(AIAssessmentJob.id)]
        result=campaign_completion_audit(db,81)
        assert result["completed_jobs"]==3
        assert result["verified_usage_backed_completed_jobs"]==1
        assert result["completed_valid_relevance_missing_linked_usage"]==2
        assert result["completed_sentiment_usage_without_classification_usage"]==1
        assert result["completed_without_valid_relevance"]==0
        assert result["completed_requiring_manual_history_review"]==2
        assert result["latest_completion_classification_review"]["completed_latest_unclassified_or_invalid"]==0
        assert result["paid_provider_called"] is False and result["database_writes"]==0
        assert [(j.id,j.state,j.attempts) for j in db.query(AIAssessmentJob).order_by(AIAssessmentJob.id)]==before
    finally:
        db.close()
        engine.dispose()
