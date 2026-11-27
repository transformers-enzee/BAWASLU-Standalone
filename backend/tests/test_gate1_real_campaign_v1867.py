"""v186.7: Politk Uang write pilot regression on disposable localhost Postgres ONLY."""
import os
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import (
    AuditEvent, CampaignEvidence, EvidenceAssessment, MonitoringCampaign,
    SocialListeningRun, SocialListeningResult, User,
)
from app.officer_sentiment import OfficerSentimentCorrection
from app.inbox_human_gate import review_source, review_queue
from app.inbox_human_corrections import (
    correct_field, decide_information, restore_field, correction_history,
    FieldCorrectionIn, DecisionIn, RestoreIn,
)
from app.inbox_human_handoff import source_feedback, gate2_handoff_preview, triage_feedback, FeedbackTriageIn
from app.inbox_gate_real_qa_v1867 import QA_ID, QA_NAME, qa_write_opt_in
from scripts.seed_gate1_render_qa_v1866 import ADMIN_EMAIL, VIEWER_EMAIL, bootstrap


def test_politik_uang_append_only_corrections(monkeypatch):
    if os.getenv("BAWASLU_ALLOW_ISOLATED_DB_TEST") != "YES":
        pytest.skip("Runs only in disposable local PostgreSQL CI")
    # Gate 1 opt-in is separate from the QA fixture bootstrap and all other writes.
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE","staging")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS","9")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_REAL_QA_CAMPAIGN_ID","9")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_REAL_QA_CONFIRM","POLITIK_UANG_AUDIT_ONLY")
    bootstrap()  # Only the expected disposable QA localhost DB.
    with Session(engine) as db:
        admin=db.scalar(select(User).where(User.email==ADMIN_EMAIL))
        viewer=db.scalar(select(User).where(User.email==VIEWER_EMAIL))
        run=db.scalar(select(SocialListeningRun))
        assert admin and viewer and run
        for i in range(2,9):
            db.add(MonitoringCampaign(
                name=f"Other test campaign {i}",status="DRAFT",created_by=str(admin.id)))
        db.flush()
        campaign=MonitoringCampaign(
            name=QA_NAME,status="DRAFT",created_by=str(admin.id),
            description="Fictional CI replica of QA campaign 9 (not real officer data).")
        db.add(campaign);db.flush()
        assert campaign.id==QA_ID and qa_write_opt_in(campaign)
        source=SocialListeningResult(
            run_id=run.id,provider="SC_DISPOSABLE_QA_ONLY",
            provider_result_id="QA-1867-FAKE",
            canonical_url="https://example.invalid/qa1867",
            text_content="Fictional money politics post test",
            platform="youtube",review_state="DISCOVERED",
            content_fingerprint="fictional-qa-1867")
        db.add(source);db.flush()
        db.add(CampaignEvidence(
            campaign_id=QA_ID,result_id=source.id,match_method="KEYWORD"))
        assessment=EvidenceAssessment(
            campaign_id=QA_ID,result_id=source.id,assessment_version=2,
            model_version="DISPOSABLE_TEST",relevance_label="UNCERTAIN",
            sentiment="NEGATIVE")
        db.add(assessment);db.commit()
        source_id=source.id; assessment_id=assessment.id
        before_assessments=db.scalar(select(func.count()).select_from(EvidenceAssessment))
        before_sources=db.scalar(select(func.count()).select_from(SocialListeningResult))
        before_sentiments=db.scalar(select(func.count()).select_from(OfficerSentimentCorrection))
        detail=review_source(QA_ID,source_id,admin,db)
        assert detail["can_review_information"] is True
        assert detail["qa_audit_only"] is True
        assert detail["original_ai_relevance"]=="UNCERTAIN"
        assert detail["relevance_revision"]==2
        first=correct_field(QA_ID,source_id,FieldCorrectionIn(
            field="relevance",value="RELEVANT",expected_revision=2,
            expected_assessment_id=assessment_id,
            expected_source_digest=detail["source_integrity_digest"],
            reason="Fictional QA override test only"),admin,db)
        assert first["saved"] and first["qa_audit_only"]
        after=review_source(QA_ID,source_id,admin,db)
        assert after["original_ai_relevance"]=="UNCERTAIN"
        assert after["effective_relevance"]=="RELEVANT"
        assert after["relevance_basis"]=="QA_OFFICER_OVERRIDE"
        assert after["relevance_revision"]==first["revision"]
        assert db.get(EvidenceAssessment,assessment_id).relevance_label=="UNCERTAIN"
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment))==before_assessments
        assert db.scalar(select(func.count()).select_from(SocialListeningResult))==before_sources
        assert db.scalar(select(func.count()).select_from(OfficerSentimentCorrection))==before_sentiments
        with pytest.raises(HTTPException) as stale:
            correct_field(QA_ID,source_id,FieldCorrectionIn(
                field="relevance",value="IRRELEVANT",expected_revision=2,
                expected_assessment_id=assessment_id,
                expected_source_digest=detail["source_integrity_digest"],
                reason="Stale fictional QA correction"),admin,db)
        assert stale.value.status_code==409
        q=review_queue(QA_ID,40,None,"all","all",admin,db)
        assert q["items"][0]["relevance"]=="RELEVANT"
        assert q["items"][0]["category"]=="relevant"
        decision=decide_information(QA_ID,source_id,DecisionIn(
            status="OFFICER_VERIFIED",expected_revision=0,
            expected_assessment_id=assessment_id,
            expected_sentiment_revision=0,
            expected_source_digest=after["source_integrity_digest"],
            reason="Fictional QA information checked and logged"),admin,db)
        assert decision["saved"] and not decision["automatic_publication"]
        reviewed=review_source(QA_ID,source_id,admin,db)
        assert reviewed["information_review_status"]=="OFFICER_VERIFIED"
        feedback=source_feedback(QA_ID,source_id,admin,db)
        assert feedback["items"][0]["correction_current"] is True
        assert feedback["items"][0]["offline_evaluation_candidate"] is False
        t=triage_feedback(QA_ID,source_id,FeedbackTriageIn(
            correction_event_id=first["correction_id"],expected_decision_revision=0,
            decision="ACCEPT_OFFLINE_EVALUATION",
            rationale="Fictional offline QA evaluation candidate",
            expected_source_digest=after["source_integrity_digest"]),admin,db)
        assert t["saved"] and not t["training_approved"]
        approved=source_feedback(QA_ID,source_id,admin,db)
        assert approved["items"][0]["offline_evaluation_candidate"] is True
        packet=gate2_handoff_preview(QA_ID,source_id,admin,db)
        assert packet["readiness"]=="BLOCKED"
        assert "QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION" in packet["review_blockers"]
        assert packet["command_centre_published"] is False
        hist=correction_history(QA_ID,source_id,admin,db)
        assert any(x["revision"]==first["revision"] for x in hist["relevance_history"])
        restored=restore_field(QA_ID,source_id,RestoreIn(
            field="relevance",target_revision=2,
            expected_revision=first["revision"],
            expected_assessment_id=assessment_id,
            expected_source_digest=after["source_integrity_digest"],
            reason="Return to original fictional AI classification"),admin,db)
        assert restored["saved"] and restored["qa_audit_only"]
        reverted=review_source(QA_ID,source_id,admin,db)
        assert reverted["effective_relevance"]=="UNCERTAIN"
        assert reverted["information_review_status"]=="REVALIDATION_REQUIRED"
        assert db.get(EvidenceAssessment,assessment_id).relevance_label=="UNCERTAIN"
        # Explicit environment disable, viewer role, and shared evidence all fail closed.
        with pytest.raises(HTTPException) as viewer_error:
            correct_field(QA_ID,source_id,FieldCorrectionIn(
                field="relevance",value="RELEVANT",expected_revision=restored["revision"],
                expected_assessment_id=assessment_id,
                expected_source_digest=reverted["source_integrity_digest"],
                reason="Viewer must not change even fictional QA"),viewer,db)
        assert viewer_error.value.status_code==403
        monkeypatch.delenv("BAWASLU_INBOX_GATE1_REAL_QA_CONFIRM")
        assert review_source(QA_ID,source_id,admin,db)["can_review_information"] is False
        monkeypatch.setenv("BAWASLU_INBOX_GATE1_REAL_QA_CONFIRM","POLITIK_UANG_AUDIT_ONLY")
        db.add(CampaignEvidence(campaign_id=8,result_id=source_id,match_method="KEYWORD"))
        db.commit()
        assert review_source(QA_ID,source_id,admin,db)["can_review_information"] is False
        with pytest.raises(HTTPException) as shared:
            correct_field(QA_ID,source_id,FieldCorrectionIn(
                field="relevance",value="RELEVANT",expected_revision=restored["revision"],
                expected_assessment_id=assessment_id,
                expected_source_digest=reverted["source_integrity_digest"],
                reason="Shared evidence is operationally protected"),admin,db)
        assert shared.value.status_code==403
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment))==before_assessments
        assert db.scalar(select(func.count()).select_from(SocialListeningResult))==before_sources
        assert db.scalar(select(func.count()).select_from(OfficerSentimentCorrection))==before_sentiments
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action=="GATE1_QA_FIELD_CORRECTED"))==2


def test_ui_qa_overrides_are_disclosed():
    from pathlib import Path
    ui=(Path(__file__).parents[2]/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    assert 'gate1-real-qa-safety' in ui
    assert "realQaSelected" in ui
