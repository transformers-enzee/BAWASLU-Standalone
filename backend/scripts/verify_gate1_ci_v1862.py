"""Post-browser audit of disposable localhost Gate 1 pilot database.

This is a second independent read-only assertion after the real UI walkthrough.
"""
import os
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import (
    AuditEvent, CampaignFindingGroup, EvidenceAssessment, IntelligenceItem,
    MonitoringCampaign, SocialListeningResult,
)
from app.officer_sentiment import OfficerSentimentCorrection
from app import inbox_human_corrections as gate
from app.inbox_gate_integrity import source_integrity_digest
from scripts.seed_gate1_ci_v1862 import assert_local_postgres


def verify():
    url=os.environ.get("DATABASE_URL","")
    assert_local_postgres(url)
    engine=create_engine(url)
    try:
        with Session(engine) as db:
            pilot=db.scalar(select(MonitoringCampaign).where(
                MonitoringCampaign.name==gate.PILOT_QA_CAMPAIGN_NAME,
            ))
            assert pilot is not None and pilot.status=="DRAFT"
            qa_source=db.scalar(select(SocialListeningResult).where(
                SocialListeningResult.provider==gate.PILOT_QA_PROVIDER,
                SocialListeningResult.provider_result_id.like("GATE1-QA-FAKE-%"),
            ))
            assert qa_source is not None
            rows=db.scalars(select(EvidenceAssessment).where(
                EvidenceAssessment.campaign_id==pilot.id,
                EvidenceAssessment.result_id==qa_source.id,
            ).order_by(EvidenceAssessment.assessment_version)).all()
            assert [row.assessment_version for row in rows]==[1,2,3]
            assert [row.relevance_label for row in rows]==[
                "IRRELEVANT","RELEVANT","IRRELEVANT",
            ]
            assert rows[0].model_version=="OFFLINE_FICTIONAL_QA"
            assert rows[0].explanation=="Fictional offline QA baseline."
            assert rows[1].model_version==rows[2].model_version=="HUMAN_OVERRIDE"
            assert qa_source.raw_payload_json=='{"fictional":true,"unchanged":true}'
            assert qa_source.promoted_intelligence_id is None
            sentiments=db.scalars(select(OfficerSentimentCorrection).where(
                OfficerSentimentCorrection.campaign_id==pilot.id,
                OfficerSentimentCorrection.result_id==qa_source.id,
            ).order_by(OfficerSentimentCorrection.id)).all()
            assert [x.sentiment for x in sentiments]==["NEUTRAL","POSITIVE"]
            events=db.scalars(select(AuditEvent).where(
                AuditEvent.subject_type=="Gate1InformationReview",
                AuditEvent.subject_id==f"{pilot.id}:{qa_source.id}",
            ).order_by(AuditEvent.id)).all()
            assert [event.action for event in events]==[
                "GATE1_FIELD_CORRECTED",
                "GATE1_FIELD_CORRECTED",
                "GATE1_INFORMATION_DECISION",
                "GATE1_FIELD_CORRECTED",
                "GATE1_FIELD_RESTORED",
            ]
            for event in events:
                assert '"model_training_triggered": false' in event.changes_json
                assert '"official_insight_published": false' in event.changes_json
            final_status=gate.review_state_for_source(
                db,pilot.id,qa_source.id,source=qa_source,
            )
            assert final_status["information_review_status"]=="REVALIDATION_REQUIRED"
            assert final_status["information_review_stale"]
            assert db.scalar(select(func.count()).select_from(IntelligenceItem))==0
            assert db.scalar(select(func.count()).select_from(CampaignFindingGroup))==0
            assert db.scalar(select(func.count()).select_from(AuditEvent))==5
            assert db.scalar(select(func.count()).select_from(
                EvidenceAssessment).where(EvidenceAssessment.campaign_id!=pilot.id)
            )==1
            assert db.scalar(select(func.count()).select_from(
                OfficerSentimentCorrection).where(OfficerSentimentCorrection.campaign_id!=pilot.id)
            )==0
        print("Post-browser PostgreSQL audit verified: exact fictional revisions, "
              "unchanged original evidence, preserved other campaign, no insight publication.")
    finally:
        engine.dispose()


if __name__=="__main__":
    verify()
