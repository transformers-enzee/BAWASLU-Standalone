"""v186.3 Gate 1 -> insight-draft preview and officer feedback governance QA.

Offline SQLite, no network, no Supabase mutation and no paid provider calls.
All source evidence is fictional, and all writes are pilot-gated.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    AccessGrant, AuditEvent, CampaignEvidence, EvidenceAssessment,
    GovernanceInsight, MonitoringCampaign, SocialListeningResult,
    SocialListeningRun, User,
)
from app.inbox_gate_integrity import source_integrity_digest
from app import inbox_human_corrections as corrections
from app import inbox_human_handoff as handoff


@pytest.fixture
def sample(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    monkeypatch.setattr(corrections, "_refresh_views", lambda: None)
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED", "true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED", "true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE", "staging")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS", "212")
    admin = User(id=57, email="fictional-admin@example.invalid",
                 full_name="Fictional Admin", password_hash="DISABLED")
    viewer = User(id=58, email="fictional-viewer@example.invalid",
                  full_name="Fictional Viewer", password_hash="DISABLED")
    campaign = MonitoringCampaign(
        id=212, name=corrections.PILOT_QA_CAMPAIGN_NAME,
        status="DRAFT", created_by="57")
    other = MonitoringCampaign(
        id=213, name="Fictional operational campaign",
        status="ACTIVE", created_by="57")
    run = SocialListeningRun(
        id=414, provider=corrections.PILOT_QA_PROVIDER,
        query_json='{"fictional":true}', status="COMPLETED",
        credits_used=0, executed_by="qa")
    post = SocialListeningResult(
        id=511, run_id=414, provider=corrections.PILOT_QA_PROVIDER,
        provider_result_id="GATE1-QA-FICTIONAL-511", platform="facebook",
        text_content="Synthetic discussion of a fictional local election.",
        raw_payload_json='{"original":"fictional"}', geography_json="{}")
    blocked = SocialListeningResult(
        id=512, run_id=414, provider="SOCIALCRAWL",
        provider_result_id="NON-QA-512",
        text_content="Protected fictional operational source", geography_json="{}")
    db.add_all([admin, viewer, campaign, other, run, post, blocked])
    db.flush()
    db.add_all([
        AccessGrant(
            user_id=admin.id, access_role="National Administrator",
            status="Active", geographic_scope="Nationwide",
            permissions_json=json.dumps({
                "view_intelligence": True, "human_validation": True,
                "edit_intelligence": True, "administration": True,
                "add_intelligence": True,
            })),
        AccessGrant(
            user_id=viewer.id, access_role="Viewer",
            status="Active", geographic_scope="Nationwide",
            permissions_json=json.dumps({"view_intelligence": True})),
        CampaignEvidence(campaign_id=212, result_id=511,
                         match_method="QA_SYNTHETIC"),
        CampaignEvidence(campaign_id=213, result_id=512,
                         match_method="KEYWORD"),
        EvidenceAssessment(
            id=711, campaign_id=212, result_id=511,
            assessment_version=1, model_version="OFFLINE_AI",
            relevance_label="IRRELEVANT", sentiment="NEGATIVE"),
        EvidenceAssessment(
            id=712, campaign_id=213, result_id=512,
            assessment_version=1, model_version="OFFLINE_AI",
            relevance_label="RELEVANT", sentiment="NEUTRAL"),
    ])
    db.commit()
    try:
        yield db, admin, viewer, post, campaign
    finally:
        db.close()
        engine.dispose()


def correct_relevance(db, admin, source, value="RELEVANT", expected_revision=1, assessment_id=711):
    return corrections.correct_field(212, source.id, corrections.FieldCorrectionIn(
        field="relevance", value=value, expected_revision=expected_revision,
        expected_assessment_id=assessment_id,
        expected_source_digest=source_integrity_digest(source),
        reason="Fictional election content is relevant for information QA",
    ), user=admin, db=db)


def review_current(db, admin, source):
    assessment=corrections._latest_assessment(db,212,source.id)
    sentiment=corrections._latest_sentiment(db,212,source.id)
    return corrections.decide_information(
        212, source.id, corrections.DecisionIn(
            status="OFFICER_VERIFIED",
            expected_revision=corrections.review_state_for_source(
                db,212,source.id)["information_review_revision"],
            expected_assessment_id=assessment.id,
            expected_sentiment_revision=sentiment.id if sentiment else 0,
            expected_source_digest=source_integrity_digest(source),
            reason="Officer reviewed the saved fictional information snapshot",
        ), user=admin, db=db,
    )


def triage(db, admin, source, event, decision="ACCEPT_OFFLINE_EVALUATION", revision=0):
    return handoff.triage_feedback(
        212, source.id, handoff.FeedbackTriageIn(
            correction_event_id=event["correction_event_id"],
            expected_decision_revision=revision,
            decision=decision,
            rationale="Fictional correction was double checked against saved evidence",
            expected_source_digest=source_integrity_digest(source),
        ),user=admin,db=db,
    )


def test_handoff_requires_review_and_relevance_and_does_not_publish(sample):
    db,admin,viewer,source,campaign=sample
    before=handoff.gate2_handoff_preview(212,511,user=admin,db=db)
    assert before["readiness"]=="BLOCKED"
    assert "ELECTION_RELEVANCE_NOT_CONFIRMED" in before["review_blockers"]
    assert "CURRENT_GATE1_INFORMATION_REVIEW_REQUIRED" in before["review_blockers"]
    assert before["command_centre_published"] is False
    correct_relevance(db,admin,source)
    not_yet=handoff.gate2_handoff_preview(212,511,user=admin,db=db)
    assert not_yet["readiness"]=="BLOCKED"
    review_current(db,admin,source)
    ready=handoff.gate2_handoff_preview(212,511,user=admin,db=db)
    assert ready["readiness"]=="CANDIDATE_FOR_INSIGHT_DRAFT"
    assert ready["review_blockers"]==[]
    assert ready["claim_status"]=="preliminary"
    assert ready["gate2_independent_approval_required"] is True
    assert ready["proposed_insight_created"] is False
    assert ready["evidence_legally_verified"] is False
    assert db.query(GovernanceInsight).count()==0
    assert source.raw_payload_json=='{"original":"fictional"}'


def test_offline_feedback_triage_is_append_only_and_requires_current_gate1_review(sample):
    db,admin,viewer,source,campaign=sample
    correct_relevance(db,admin,source)
    response=handoff.source_feedback(212,511,user=admin,db=db)
    assert response["can_triage"] is True
    assert len(response["items"])==1
    item=response["items"][0]
    assert item["triage_decision"]=="UNREVIEWED"
    assert item["training_approved"] is False
    with pytest.raises(HTTPException) as exc:
        triage(db,admin,source,item)
    assert exc.value.status_code==409
    review_current(db,admin,source)
    accepted=triage(db,admin,source,item)
    assert accepted["saved"]
    assert accepted["automatic_training"] is False
    assert accepted["training_approved"] is False
    assert accepted["automatic_publication"] is False
    updated=handoff.source_feedback(212,511,user=admin,db=db)["items"][0]
    assert updated["triage_decision"]=="ACCEPT_OFFLINE_EVALUATION"
    assert updated["offline_evaluation_candidate"] is True
    assert updated["triage_revision"]==accepted["triage_revision"]
    with pytest.raises(HTTPException) as conflict:
        triage(db,admin,source,item)
    assert conflict.value.status_code==409
    triage(db,admin,source,item,"REJECT_OFFLINE_EVALUATION",
           revision=accepted["triage_revision"])
    latest=handoff.source_feedback(212,511,user=admin,db=db)["items"][0]
    assert latest["triage_decision"]=="REJECT_OFFLINE_EVALUATION"
    events=(db.query(AuditEvent)
            .filter_by(subject_type=handoff.FEEDBACK_SUBJECT).order_by(AuditEvent.id).all())
    assert len(events)==2
    assert events[0].id!=events[1].id
    assert all(json.loads(e.changes_json)["training_approved"] is False for e in events)
    assert db.query(GovernanceInsight).count()==0


def test_newer_correction_marks_offline_feedback_stale_and_blocks_handoff(sample):
    db,admin,viewer,source,campaign=sample
    correct_relevance(db,admin,source)
    review_current(db,admin,source)
    item=handoff.source_feedback(212,511,user=admin,db=db)["items"][0]
    triage(db,admin,source,item)
    # New sentiment override invalidates the existing whole-information QA.
    assessment=corrections._latest_assessment(db,212,511)
    corrections.correct_field(212,511,corrections.FieldCorrectionIn(
        field="sentiment", value="NEUTRAL", expected_revision=0,
        expected_assessment_id=assessment.id,
        expected_source_digest=source_integrity_digest(source),
        reason="Fictional discussion is neutral after context review",
    ),user=admin,db=db)
    packet=handoff.gate2_handoff_preview(212,511,user=admin,db=db)
    assert packet["readiness"]=="BLOCKED"
    assert packet["gate1_review_status"]=="REVALIDATION_REQUIRED"
    feedback=handoff.source_feedback(212,511,user=admin,db=db)
    original=next(x for x in feedback["items"] if x["correction_event_id"]==item["correction_event_id"])
    assert original["offline_evaluation_candidate"] is False
    # A superseded relevance correction cannot be newly accepted even after
    # the information itself gets re-reviewed.
    correct_relevance(db,admin,source,"UNCERTAIN",2,assessment.id)
    review_current(db,admin,source)
    with pytest.raises(HTTPException) as exc:
        triage(db,admin,source,item,"ACCEPT_OFFLINE_EVALUATION",
               revision=original["triage_revision"])
    assert exc.value.status_code==409
    assert source.raw_payload_json=='{"original":"fictional"}'


def test_feedback_queue_is_scoped_paginated_and_never_claims_population_counts(sample):
    db,admin,viewer,source,campaign=sample
    correct_relevance(db,admin,source)
    a=corrections._latest_assessment(db,212,511)
    corrections.correct_field(212,511,corrections.FieldCorrectionIn(
        field="sentiment",value="NEUTRAL",expected_revision=0,
        expected_assessment_id=a.id,expected_source_digest=source_integrity_digest(source),
        reason="Fictional review confirms neutral language",
    ),user=admin,db=db)
    page1=handoff.campaign_feedback(212,limit=1,user=viewer,db=db)
    assert page1["page_count"]==1
    assert page1["has_more"] is True
    assert page1["not_population_totals"] is True
    page2=handoff.campaign_feedback(
        212,cursor=page1["next_cursor"],limit=1,user=viewer,db=db)
    assert len(page2["items"])==1
    assert page1["items"][0]["correction_event_id"]!=page2["items"][0]["correction_event_id"]
    assert page2["has_more"] is False
    assert all(item["result_id"]=="511" for item in page1["items"]+page2["items"])
    assert handoff.campaign_feedback(213,user=admin,db=db)["items"]==[]
    with pytest.raises(HTTPException) as exc:
        handoff.campaign_feedback(212,limit=1000,user=viewer,db=db)
    assert exc.value.status_code==422
    with pytest.raises(HTTPException) as exc:
        handoff.source_feedback(212,512,user=admin,db=db)
    assert exc.value.status_code==404


def test_viewer_cannot_triage_and_operational_campaign_never_writable(sample):
    db,admin,viewer,source,campaign=sample
    correct_relevance(db,admin,source)
    item=handoff.source_feedback(212,511,user=viewer,db=db)["items"][0]
    assert handoff.source_feedback(212,511,user=viewer,db=db)["can_triage"] is False
    with pytest.raises(HTTPException) as exc:
        triage(db,viewer,source,item,"NEEDS_RECHECK")
    assert exc.value.status_code==403
    with pytest.raises(HTTPException) as exc:
        handoff.triage_feedback(213,512,handoff.FeedbackTriageIn(
            correction_event_id=item["correction_event_id"],
            expected_decision_revision=0,decision="NEEDS_RECHECK",
            rationale="Should be restricted to fictional pilot sources",
            expected_source_digest=source_integrity_digest(source),
        ),user=admin,db=db)
    assert exc.value.status_code==403
    assert db.query(AuditEvent).filter_by(subject_type=handoff.FEEDBACK_SUBJECT).count()==0


def test_ui_and_routes_are_read_only_by_default():
    root=__import__("pathlib").Path(__file__).resolve().parents[2]
    main=(root/"backend/app/main.py").read_text()
    ui=(root/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    api=(root/"frontend/src/api/base44Client.js").read_text()
    handoff_source=(root/"backend/app/inbox_human_handoff.py").read_text()
    assert "inbox_human_handoff_router" in main
    for item in ("gate1-gate2-readiness","gate1-feedback-queue",
                 "gate1-offline-feedback","gate1-feedback-triage",
                 "Gate 3 must separately govern"):
        assert item in ui
    for item in ("gate2Readiness:","sourceFeedback:","campaignFeedback:",
                 "triageFeedback:"):
        assert item in api
    assert "training_triggered\": False" in handoff_source
    assert "model_promotion_approved\": False" in handoff_source
    assert "command_centre_published\": False" in handoff_source
    assert "_authorize(db, user, campaign_id, result_id, True)" in handoff_source
    assert "db.delete(" not in handoff_source
    assert "db.add(GovernanceInsight" not in handoff_source
