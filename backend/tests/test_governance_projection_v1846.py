"""v184.6 governance projection, source changes, fail-closed release guards."""
from types import SimpleNamespace
from fastapi import HTTPException
from app.governance_projection import effective_assessment, source_snapshot_fingerprint
from app.governance_persistence import (
    CorrectionIn, InsightIn, _approved_row_gate, _enabled, approved_command_centre,
)
import pytest


def record(**kwargs):
    return SimpleNamespace(**kwargs)


def test_officer_precedence_is_per_field_not_entire_record():
    ai=record(id=2, assessment_version=3, model_version="model-a",
              relevance_label="RELEVANT", sentiment="NEUTRAL")
    c1=record(id=1,field="sentiment",status="approved",human_value="NEGATIVE",
              revision=1,reviewer_id=4)
    c2=record(id=2,field="sentiment",status="proposed",human_value="POSITIVE",
              revision=2,reviewer_id=5)
    result=effective_assessment(ai,[c1,c2])
    assert result["fields"]["sentiment"]["effective_value"]=="NEGATIVE"
    assert result["fields"]["sentiment"]["effective_basis"]=="OFFICER_APPROVED"
    assert result["fields"]["relevance"]["effective_value"]=="RELEVANT"
    assert result["record_human_verified"] is False


def test_unknown_ai_fields_are_not_fabricated():
    c=record(id=1,field="narrative",status="approved",human_value="Sample",
             revision=1,reviewer_id=4)
    result=effective_assessment(None,[c])
    assert result["fields"]["sentiment"]["effective_value"] is None
    assert result["unmapped_correction_fields"]==["narrative"]


def test_fingerprint_invalidates_on_original_text_ai_or_any_review():
    original=record(id=1,text_content="pemilu",canonical_url="https://example.org/post",
                    content_fingerprint="v1")
    ai=record(id=2,sentiment="NEUTRAL",model_version="m")
    a=record(id=1,field="sentiment",status="approved",human_value="NEGATIVE",
             revision=1,reviewer_id=3)
    b=record(id=2,field="narrative",status="approved",human_value="Other",
             revision=1,reviewer_id=4)
    baseline=source_snapshot_fingerprint(original,ai,[a])
    assert baseline==source_snapshot_fingerprint(original,ai,[a])
    assert baseline!=source_snapshot_fingerprint(
        record(id=1,text_content="changed",canonical_url="https://example.org/post",
               content_fingerprint="v1"),ai,[a])
    assert baseline!=source_snapshot_fingerprint(original,
        record(id=2,sentiment="POSITIVE",model_version="m"),[a])
    assert baseline!=source_snapshot_fingerprint(original,ai,[a,b])


def test_approved_feed_gate_rejects_stale_and_unverified_claims():
    row=record(id=3,state="approved",approver_id=10,revision=2,
               analysis_scope="2026-11",claim_status="preliminary",
               evidence_verified=False,contains_high_impact_claims=False,
               high_impact_reviewed=False)
    assert _approved_row_gate(row,[9],True)["publish_allowed"]
    assert not _approved_row_gate(row,[9],False)["publish_allowed"]
    row.claim_status="verified"
    assert not _approved_row_gate(row,[9],True)["publish_allowed"]


def test_model_does_not_accept_unbounded_or_false_verified_claims():
    assert InsightIn(campaign_id=1,title="Election discussion",
                     evidence_result_ids=[1],analysis_scope="2026-11").claim_status=="preliminary"
    with pytest.raises(Exception):
        InsightIn(campaign_id=1,title="Election discussion",
                  evidence_result_ids=list(range(101)),analysis_scope="2026-11")


def test_feature_flag_stays_closed_by_default(monkeypatch):
    monkeypatch.delenv("BAWASLU_GOVERNANCE_WRITES_ENABLED",raising=False)
    with pytest.raises(HTTPException) as exc:
        _enabled()
    assert exc.value.status_code==503


def test_no_browser_bypass_in_approved_feed_source():
    import inspect
    src=inspect.getsource(approved_command_centre)
    assert '_approved_row_gate' in src
    assert '_snapshot' in src
