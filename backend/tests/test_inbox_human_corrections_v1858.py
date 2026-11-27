"""v185.8 Human Gate 1 append-only correction, restore, status and RBAC QA."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    User, MonitoringCampaign, SocialListeningResult,
    EvidenceAssessment, EvidenceReview, AuditEvent,
)
from app.officer_sentiment import OfficerSentimentCorrection
from app import inbox_human_corrections as gate


@pytest.fixture
def seeded(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(id=701, email="qa-officer@example.invalid", password_hash="hash", full_name="Officer QA")
    campaign = MonitoringCampaign(id=300, name="Election QA", status="ACTIVE", created_by="701")
    source = SocialListeningResult(id=801, run_id=1, text_content="A saved election discussion",
                                   platform="facebook", raw_payload_json='{"Message":"unchanged"}')
    assessment = EvidenceAssessment(
        id=900, campaign_id=300, result_id=801, assessment_version=1,
        model_version="AI_BASE", relevance_label="UNCERTAIN", sentiment="NEGATIVE",
        candidate_signals_json='["example"]', topic_labels_json='["elections"]',
    )
    db.add_all([user, campaign, source, assessment])
    db.commit()
    monkeypatch.setattr(gate, "_refresh_views", lambda: None)
    return db, user, campaign, source


def profile():
    return {"id":"701", "name":"Officer QA", "status":"Active",
            "permissions":{"view_intelligence":True,"human_validation":True,
                           "edit_intelligence":True,"add_intelligence":True},
            "role":"National Administrator", "geographic_scope":"Nationwide"}


def test_write_denied_by_default_and_requires_pilot_allowlist(monkeypatch, seeded):
    db,user,campaign,source=seeded
    p=profile()
    monkeypatch.delenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED",raising=False)
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE","staging")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS","300")
    assert gate.can_edit_gate1(p,campaign) is False
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
    assert gate.can_edit_gate1(p,campaign) is True
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS","*")
    assert gate.can_edit_gate1(p,campaign) is False
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS","999")
    assert gate.can_edit_gate1(p,campaign) is False
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS","300")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE","production")
    assert gate.can_edit_gate1(p,campaign) is False
    restricted={**p,"permissions":{**p["permissions"],"human_validation":False}}
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE","staging")
    assert gate.can_edit_gate1(restricted,campaign) is False
    db.close()


def test_field_correction_restore_and_audit_integrity(seeded):
    db,user,campaign,source=seeded
    p=profile()
    changed=gate._apply_field(db,user,p,source,300,"relevance","RELEVANT",1,
                              "Source concerns an election candidate")
    assert changed["revision"] == 2
    latest=gate._latest_assessment(db,300,801)
    assert latest.relevance_label=="RELEVANT"
    assert latest.model_version=="HUMAN_OVERRIDE"
    assert latest.topic_labels_json=='["elections"]'
    assert db.get(EvidenceAssessment,900).relevance_label=="UNCERTAIN"
    with pytest.raises(HTTPException) as conflict:
        gate._apply_field(db,user,p,source,300,"relevance","IRRELEVANT",1,
                          "Old form submission must be rejected")
    assert conflict.value.status_code==409
    sentiment=gate._apply_field(db,user,p,source,300,"sentiment","NEUTRAL",0,
                                "Sentiment is not negative in context")
    assert sentiment["revision"] > 0
    assert gate._latest_sentiment(db,300,801).sentiment=="NEUTRAL"
    assert db.get(SocialListeningResult,801).raw_payload_json=='{"Message":"unchanged"}'
    monkeypatch_auth=lambda db,user,cid,rid,write=False:(p,campaign,source)
    original=gate._authorize
    gate._authorize=monkeypatch_auth
    try:
        restored=gate.restore_field(
            300,801,gate.RestoreIn(field="relevance",target_revision=1,
                                   expected_revision=2,expected_assessment_id=changed["correction_id"],
                                   expected_source_digest=gate.source_integrity_digest(source),
                                   reason="Restore original AI assessment for review"),
            user=user,db=db)
        assert restored["revision"]==3
        assert gate._latest_assessment(db,300,801).relevance_label=="UNCERTAIN"
        history=gate.correction_history(300,801,user=user,db=db)
        assert [row["revision"] for row in history["relevance_history"][:3]]==[3,2,1]
        assert history["audit_history"][0]["action"]=="GATE1_FIELD_RESTORED"
    finally:
        gate._authorize=original
        db.close()


def test_review_decision_becomes_stale_after_new_correction(seeded, monkeypatch):
    db,user,campaign,source=seeded
    p=profile()
    monkeypatch.setattr(gate,"_authorize",lambda db,user,cid,rid,write=False:(p,campaign,source))
    digest=gate.source_integrity_digest(source)
    result=gate.decide_information(
        300,801,gate.DecisionIn(status="OFFICER_VERIFIED",expected_revision=0,
                               expected_assessment_id=900,expected_sentiment_revision=0,
                               expected_source_digest=digest,
                               reason="Officer inspected original evidence and attribution"),
        user=user,db=db)
    assert result["legal_claim_verified"] is False
    assert gate.review_state_for_source(db,300,801)["information_review_status"]=="OFFICER_VERIFIED"
    with pytest.raises(HTTPException) as exc:
        gate.decide_information(
            300,801,gate.DecisionIn(status="EXCLUDED",expected_revision=0,
                                   expected_assessment_id=900,expected_sentiment_revision=0,
                                   expected_source_digest=digest,
                                   reason="Stale decision must be rejected"),user=user,db=db)
    assert exc.value.status_code==409
    gate._apply_field(db,user,p,source,300,"relevance","RELEVANT",1,
                      "New source context supports relevance")
    state=gate.review_state_for_source(db,300,801)
    assert state["information_review_stale"]
    assert state["information_review_status"]=="REVALIDATION_REQUIRED"
    db.close()


def test_scope_is_enforced_before_mutations(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.setattr(gate,"_grant",lambda db,user,permission:profile())
    monkeypatch.setattr(gate,"_campaign",lambda db,p,cid:SimpleNamespace(id=cid))
    def deny(*args):raise HTTPException(404,"Source unavailable")
    monkeypatch.setattr(gate,"_source",deny)
    with pytest.raises(HTTPException) as exc:
        gate.correct_field(
            300,999,gate.FieldCorrectionIn(field="relevance",value="RELEVANT",
                                            expected_revision=1,expected_assessment_id=900,
                                            expected_source_digest="0"*64,
                                            reason="Reviewer explanation"),
            user=SimpleNamespace(id=701),db=MagicMock())
    assert exc.value.status_code==404


def test_client_controls_and_runtime_gates_present():
    root=Path(__file__).resolve().parents[2]
    api=(root/"frontend/src/api/base44Client.js").read_text()
    ui=(root/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    server=(root/"backend/app/inbox_human_corrections.py").read_text()
    for item in ("gate1-save-field-correction", "gate1-save-review-decision",
                 "gate1-audit-history", "information_review_status",
                 "base44.inboxHumanReview.restore"):
        assert item in ui
    for item in ("/corrections", "/restore", "/decision", "/history"):
        assert item in api
    for item in ("with_for_update()", "expected_revision", "_source(db, officer",
                 "model_training_triggered", "official_insight_published",
                 "_allowlist()", "human_validation", "edit_intelligence"):
        assert item in server
    assert "db.delete(" not in server
    assert "db.query(GovernanceInsight)" not in server
