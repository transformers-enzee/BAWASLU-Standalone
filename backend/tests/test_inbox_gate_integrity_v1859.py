"""v185.9: source-snapshot freshness, optimistic edits, QA triage & integration QA."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (
    AuditEvent, CampaignEvidence, EvidenceAssessment, MonitoringCampaign,
    SocialListeningResult, User,
)
from app import inbox_human_corrections as gate
from app import inbox_human_queue as queue
from app.inbox_gate_integrity import (
    audit_payload, review_projection, review_status_matches,
    saved_relevance_basis, source_integrity_digest,
)


def info_profile():
    return {
        "id": "40", "name": "Review officer", "status": "Active",
        "role": "National Administrator", "geographic_scope": "Nationwide",
        "permissions": {
            "view_intelligence": True, "human_validation": True,
            "edit_intelligence": True, "add_intelligence": True,
            "administration": True,
        },
    }


@pytest.fixture
def staging_db(monkeypatch):
    # No remote Supabase connection or paid AI request.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(id=40, email="qa@example.invalid", full_name="Review officer",
                password_hash="hash")
    campaign = MonitoringCampaign(id=90, name="Staging review", created_by="40",
                                  status="ACTIVE")
    posts = [
        SocialListeningResult(
            id=101+i, run_id=1, platform="facebook",
            text_content="Original saved post "+str(i),
            canonical_url="https://example.org/post/"+str(i),
            raw_payload_json='{"provider":"immutable"}',
        ) for i in range(3)
    ]
    assessments = [
        EvidenceAssessment(
            id=701+i, campaign_id=90, result_id=101+i,
            assessment_version=1, model_version="AI_V1",
            relevance_label=["RELEVANT", "UNCERTAIN", "IRRELEVANT"][i],
            sentiment="NEUTRAL",
        ) for i in range(3)
    ]
    links = [
        CampaignEvidence(id=901+i, campaign_id=90, result_id=101+i,
                         match_method="KEYWORD") for i in range(3)
    ]
    db.add_all([user, campaign, *posts, *assessments, *links])
    db.commit()
    monkeypatch.setattr(gate, "_refresh_views", lambda: None)
    yield db, user, posts, assessments
    db.close()
    engine.dispose()


def officer_api(monkeypatch, posts):
    p = info_profile()
    monkeypatch.setattr(
        gate, "_authorize",
        lambda db, user, campaign_id, result_id, write=False:
            (p, SimpleNamespace(id=90), db.get(SocialListeningResult, result_id)),
    )
    return p


def tokens(source, assessment, sentiment_id=0, revision=0, status="OFFICER_VERIFIED"):
    return gate.DecisionIn(
        status=status, expected_revision=revision,
        expected_assessment_id=assessment.id,
        expected_sentiment_revision=sentiment_id,
        expected_source_digest=source_integrity_digest(source),
        reason="Officer inspected the original information in full",
    )


def audit_review(db, source, assessment, status):
    event = AuditEvent(
        subject_type="Gate1InformationReview",
        subject_id=f"90:{source.id}", action="GATE1_INFORMATION_DECISION",
        actor_id="40", actor_name="Review officer",
        changes_json=json.dumps({
            "status": status, "reason": "Officer information QA",
            "assessment_id": assessment.id,
            "sentiment_correction_id": None,
            "source_integrity_digest": source_integrity_digest(source),
        }),
        occurred_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(event)
    db.commit()
    return event


def test_snapshot_digest_changes_without_exposing_raw_content():
    source = SimpleNamespace(
        id=8, run_id=3, provider="SOCIALCRAWL", provider_result_id="x",
        platform="instagram", canonical_url="https://example.org/x",
        author_name="Public author", published_at="2026-11-26",
        text_content="Original post", content_fingerprint="abc",
    )
    before = source_integrity_digest(source)
    source.text_content = "Replaced post"
    after = source_integrity_digest(source)
    assert before != after
    assert len(after) == 64
    assert "Replaced post" not in after
    assert source_integrity_digest(source) == after


def test_previous_decision_without_digest_fails_closed():
    source=SimpleNamespace(id=9,text_content="Saved")
    assessment=SimpleNamespace(id=13)
    legacy=SimpleNamespace(
        id=2, actor_id="40", occurred_at="2026-11-26T01:00Z",
        changes_json=json.dumps({"status":"OFFICER_VERIFIED",
                                 "assessment_id":13,"sentiment_correction_id":None}),
    )
    result=review_projection(legacy,assessment,None,source)
    assert result["information_review_status"]=="REVALIDATION_REQUIRED"
    assert result["information_review_stale"] is True
    assert result["information_review_revision"]==2
    assert review_status_matches(result,"revalidation_required")
    assert not review_status_matches(result,"officer_verified")


def test_review_snapshot_is_invalidated_by_saved_source_change(staging_db, monkeypatch):
    db,user,posts,assessments=staging_db
    officer_api(monkeypatch,posts)
    body=tokens(posts[0],assessments[0])
    outcome=gate.decide_information(90,101,body,user=user,db=db)
    assert outcome["status"]=="OFFICER_VERIFIED"
    assert gate.review_state_for_source(db,90,101)["information_review_status"]=="OFFICER_VERIFIED"

    posts[0].text_content="Post text updated after officer review"
    db.commit()
    changed=gate.review_state_for_source(db,90,101)
    assert changed["information_review_stale"]
    assert changed["information_review_status"]=="REVALIDATION_REQUIRED"
    with pytest.raises(HTTPException) as err:
        gate.decide_information(
            90,101,gate.DecisionIn(
                status="EXCLUDED", expected_revision=outcome["revision"],
                expected_assessment_id=assessments[0].id,
                expected_sentiment_revision=0,
                expected_source_digest=body.expected_source_digest,
                reason="Officer review should reject a stale source snapshot",
            ),user=user,db=db,
        )
    assert err.value.status_code==409


def test_old_assessment_id_blocks_new_field_correction(staging_db, monkeypatch):
    db,user,posts,assessments=staging_db
    officer_api(monkeypatch,posts)
    original_payload=posts[0].raw_payload_json
    original_assessment=assessments[0]
    digest=source_integrity_digest(posts[0])
    with pytest.raises(HTTPException) as err:
        gate.correct_field(
            90,101,gate.FieldCorrectionIn(
                field="relevance",value="IRRELEVANT",expected_revision=1,
                expected_assessment_id=9999,expected_source_digest=digest,
                reason="Request came from a stale review tab",
            ),user=user,db=db,
        )
    assert err.value.status_code==409
    corrected=gate.correct_field(
        90,101,gate.FieldCorrectionIn(
            field="relevance",value="IRRELEVANT",expected_revision=1,
            expected_assessment_id=original_assessment.id,expected_source_digest=digest,
            reason="Irrelevant to the monitored election",
        ),user=user,db=db,
    )
    assert corrected["saved"] and corrected["automatic_publication"] is False
    assert posts[0].raw_payload_json==original_payload
    assert original_assessment.relevance_label=="RELEVANT"
    assert gate._latest_assessment(db,90,101).model_version=="HUMAN_OVERRIDE"
    assert saved_relevance_basis(gate._latest_assessment(db,90,101))=="OFFICER_CORRECTION"
    with pytest.raises(HTTPException) as err:
        gate.correct_field(
            90,101,gate.FieldCorrectionIn(
                field="sentiment",value="NEGATIVE",expected_revision=0,
                expected_assessment_id=original_assessment.id,
                expected_source_digest=digest,
                reason="Attempting correction after the AI assessment changed",
            ),user=user,db=db,
        )
    assert err.value.status_code==409


def test_old_source_digest_blocks_correction_with_current_assessment(staging_db,monkeypatch):
    db,user,posts,assessments=staging_db
    officer_api(monkeypatch,posts)
    old_digest=source_integrity_digest(posts[1])
    posts[1].text_content="Newer saved source contents"
    db.commit()
    with pytest.raises(HTTPException) as err:
        gate.correct_field(
            90,102,gate.FieldCorrectionIn(
                field="sentiment",value="NEGATIVE",expected_revision=0,
                expected_assessment_id=assessments[1].id,
                expected_source_digest=old_digest,
                reason="A correction must require current source data",
            ),user=user,db=db,
        )
    assert err.value.status_code==409


def test_incomplete_ai_assessment_cannot_be_officer_verified(staging_db,monkeypatch):
    db,user,posts,assessments=staging_db
    officer_api(monkeypatch,posts)
    assessments[1].model_version="PRISM_PENDING_OPENAI"
    assessments[1].relevance_label="UNASSESSED"
    db.commit()
    with pytest.raises(HTTPException) as err:
        gate.decide_information(
            90,102,tokens(posts[1],assessments[1]),user=user,db=db,
        )
    assert err.value.status_code==422
    assert gate._latest_decision(db,90,102) is None


def test_queue_status_filter_scans_authorized_campaign_only(staging_db):
    db,user,posts,assessments=staging_db
    audit_review(db,posts[0],assessments[0],"OFFICER_VERIFIED")
    audit_review(db,posts[2],assessments[2],"HELD")
    posts[2].text_content="Source changed"
    db.commit()
    p=info_profile()
    reviewed=queue.paginated_review_queue(db,p,90,review_status="officer_verified")
    assert [x["result_id"] for x in reviewed["items"]]==["101"]
    assert reviewed["count_is_page_only"] is True
    assert reviewed["page_review_status_counts"]["OFFICER_VERIFIED"]==1
    recheck=queue.paginated_review_queue(db,p,90,review_status="revalidation_required")
    assert [x["result_id"] for x in recheck["items"]]==["103"]
    pending=queue.paginated_review_queue(db,p,90,review_status="needs_review")
    assert [x["result_id"] for x in pending["items"]]==["102"]
    excluded=queue.paginated_review_queue(
        db,p,90,review_status="revalidation_required",category="excluded",
    )
    assert [x["result_id"] for x in excluded["items"]]==["103"]
    with pytest.raises(HTTPException) as err:
        queue.paginated_review_queue(db,p,90,review_status="invalid")
    assert err.value.status_code==422


def test_gate1_ux_separates_effective_from_ai_and_requires_fresh_tokens():
    root=Path(__file__).resolve().parents[2]
    ui=(root/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    client=(root/"frontend/src/api/base44Client.js").read_text()
    gate_source=(root/"backend/app/inbox_human_gate.py").read_text()
    for item in ("gate1-review-status-filter", "gate1-qa-coverage",
                 "Original AI relevance", "Effective relevance",
                 "expected_assessment_id:detail.assessment_id",
                 "expected_source_digest:detail.source_integrity_digest"):
        assert item in ui
    assert "review_status:reviewStatus" in client
    assert "ai_baseline" in gate_source
    assert "saved_relevance_basis" in gate_source
    assert "source_integrity_digest" in gate_source or "review_state_for_source" in gate_source


def test_write_rechecks_geographic_scope_after_source_lock(staging_db, monkeypatch):
    db, user, posts, assessments = staging_db
    # Initial API access is mocked to isolate the post-lock geography guard:
    # a regional reviewer must never inherit nationwide access accidentally.
    regional = {
        **info_profile(), "geographic_scope": "Province",
        "province": "Jawa Barat", "province_code": "32",
    }
    monkeypatch.setattr(
        gate, "_authorize",
        lambda db, user, cid, rid, write=False:
            (regional, SimpleNamespace(id=90), db.get(SocialListeningResult, rid)),
    )
    with pytest.raises(HTTPException) as err:
        gate.correct_field(
            90,101,gate.FieldCorrectionIn(
                field="relevance", value="IRRELEVANT", expected_revision=1,
                expected_assessment_id=assessments[0].id,
                expected_source_digest=source_integrity_digest(posts[0]),
                reason="This source is not in the officer's assignment",
            ), user=user, db=db,
        )
    assert err.value.status_code == 404
    assert gate._latest_assessment(db,90,101).relevance_label == "RELEVANT"


def test_administrator_read_only_pilot_preflight(staging_db, monkeypatch):
    from app import inbox_human_gate as api
    db, user, posts, assessments = staging_db
    p = info_profile()
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED", "true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED", "false")
    monkeypatch.delenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS", raising=False)
    monkeypatch.setattr(api, "_grant", lambda db, u, permission: p)
    monkeypatch.setattr(
        api, "_campaign",
        lambda db, p, cid: db.get(MonitoringCampaign, cid),
    )
    result = api.gate1_pilot_readiness(90, user=user, db=db)
    assert result["campaign_id"] == "90"
    assert result["correction_writes_enabled"] is False
    assert result["ready_for_write_pilot"] is False
    assert result["officer_can_edit_campaign"] is True
    assert result["writes_triggered"] is False
    assert result["source_ids_exposed"] is False
    assert db.query(AuditEvent).count() == 0
    monkeypatch.setattr(
        api, "_grant",
        lambda db,u,permission: (_ for _ in ()).throw(
            HTTPException(403, "Administrator required")),
    )
    with pytest.raises(HTTPException) as denied:
        api.gate1_pilot_readiness(90, user=user, db=db)
    assert denied.value.status_code == 403
