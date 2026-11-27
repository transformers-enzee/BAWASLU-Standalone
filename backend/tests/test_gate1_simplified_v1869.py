"""v186.9: simplified operator UX contracts and unchanged governance safeguards."""
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.inbox_human_full_review_v1868 import (
    FIELDS, SENSITIVE, FieldPatch, ManualEvidenceIn, _safe_url,
)

ROOT = Path(__file__).resolve().parents[2]


def test_two_action_interface_and_inline_field_editing():
    source=(ROOT/"frontend/src/components/intel/Gate1FullWorkbench.jsx").read_text()
    assert source.count('role="tab"') == 2
    for name in ("gate1-action-review","gate1-action-missing",
                 "gate1-quick-field-select","gate1-quick-value",
                 "gate1-save-quick-correction","gate1-save-and-next",
                 "gate1-one-click-approve","gate1-automatic-quality-hints",
                 "gate1-manual-intake","gate1-secondary-review",
                 "gate1-full-audit-history","gate1-full-field-workbench"):
        assert name in source, name
    assert "savedIssues(detail,view)" in source
    assert "Automatic saved-data checks, not confirmed errors" in source
    assert "not a Social Listening record" in source
    assert "sourceConfirmed?'SOURCE_CONFIRMED':'UNVERIFIED'" in source
    assert "autoFieldReason" in source
    assert "System-generated QA audit note" in source
    assert "Officer chose to hold" in source
    assert "Official" not in source.split("autoDecisionReason=")[0]
    assert "Add to review batch" not in source
    assert "Verification level" not in source
    assert "Change type" not in source


def test_old_high_friction_form_not_shown_to_campaign_9():
    source=(ROOT/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    assert "!(realQaSelected&&detail.qa_audit_only)" in source
    assert "onNext={nextReviewSource}" in source
    assert "function nextReviewSource()" in source
    assert "gate1-correction-workbench" in source  # retained for the synthetic QA pilot
    assert "Pilot safeguards & readiness (optional)" in source
    assert "Advanced: Insight handoff checks" in source


def test_backend_high_impact_controls_remain_mandatory():
    source=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    assert "A second officer must independently review these changes" in source
    assert "can_secondary_review" in source
    assert '"can_secondary_review":secondary_allowed' in source
    assert "official_insight_published" in source
    assert "model_training_triggered" in source
    assert "source_integrity_digest" in source
    assert "expected_assessment_id" in source
    assert "expected_revision" in source
    assert "qa_audit_only" in source
    assert "candidate_names" in SENSITIVE
    assert "country" in SENSITIVE
    assert "potential_issue_categories" in SENSITIVE
    assert "engagement_likes" in FIELDS
    assert "transcript" in FIELDS
    with pytest.raises(ValidationError):
        FieldPatch(field="language",value="id",field_reason="short")
    with pytest.raises(ValidationError):
        ManualEvidenceIn(platform="youtube",title="QA",text_content="short",reason="short")
    with pytest.raises(HTTPException) as bad:
        _safe_url("javascript:alert(1)",True)
    assert bad.value.status_code == 422


def test_original_source_and_review_publication_paths_unchanged():
    router=(ROOT/"backend/app/inbox_human_gate.py").read_text()
    handoff=(ROOT/"backend/app/inbox_human_handoff.py").read_text()
    corrections=(ROOT/"backend/app/inbox_human_corrections.py").read_text()
    assert "QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION" in handoff
    assert "OFFICER_VERIFIED" in corrections
    assert "Independent officer approval required" in corrections
    assert 'full_field_revision' in router
    # Digest validation is owned by the correction handler, not the read-only Inbox route.
    assert "source_integrity_digest" in corrections
    full=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    assert "source_integrity_digest" in full
