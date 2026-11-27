"""BAWASLU v187.9 - officer variable control UX and immutable QA contracts.

Tests examine the actual pilot-mounted component, not the retained legacy
workbench, and never write to a connected officer database.
"""
from pathlib import Path

from app.inbox_human_full_review_v1868 import (
    ASSESSMENT_FIELDS, FIELDS, SENSITIVE, COMPLETABLE_FIELDS, TECHNICAL_READ_ONLY_FIELDS
)
from app.inbox_gate1_review_plan_v1875 import AREAS

ROOT = Path(__file__).resolve().parents[2]
UI_PATH = ROOT / "frontend/src/components/intel/Gate1VariableControlV1879.jsx"
PARENT_PATH = ROOT / "frontend/src/components/intel/InboxHumanReview.jsx"


def test_selected_pilot_mounts_direct_field_editor_not_decision_workbench():
    parent = PARENT_PATH.read_text()
    assert "import Gate1VariableControlV1879 from './Gate1VariableControlV1879'" in parent
    assert "<Gate1VariableControlV1879 campaignId={campaignId} detail={detail}" in parent
    assert "(String(campaignId)==='9'&&detail.qa_audit_only)" in parent
    assert "gate1-extended-assessment-details" in parent
    assert "open={!realQaSelected}" in parent


def test_variable_values_have_visible_inline_edit_or_add_and_single_field_save():
    ui = UI_PATH.read_text()
    for expected in (
        "gate1-variable-control-v1879","gate1-priority-values",
        "gate1-inline-editor","gate1-inline-save","gate1-inline-value",
        "gate1-effective-","gate1-edit-","Save value","Save & Next",
        "Original value","Current", "setField(key)","setDraft(",
        "gate1-other-intelligence-values","gate1-all-permitted-values",
        "gate1-all-values-search","gate1-contextual-hints",
    ):
        assert expected in ui,expected
    # No mandatory approval/status decision before editing the effective value.
    assert "inboxHumanReview.decide(" not in ui
    assert "OFFICER_VERIFIED" not in ui
    assert "Hold for verification" not in ui
    assert "Complete Missing Data" not in ui
    assert "Add Missing Post" not in ui


def test_all_eight_dimensions_remain_covered_with_three_focus_areas():
    ui=UI_PATH.read_text()
    assert ui.count("en:'") >= 8
    assert "GROUPS.slice(0,3)" in ui
    assert "GROUPS.slice(3)" in ui
    assert [area["id"] for area in AREAS[:3]] == ["violation","actors","jurisdiction"]
    assert "incident_jurisdiction" in ui
    assert "potential_issue_categories" in ui
    assert "candidate_names" in ui


def test_source_and_technical_fields_use_role_guard_not_unrestricted_edit():
    ui=UI_PATH.read_text()
    assert "view?.can_edit" in ui
    assert "view?.can_correct_source" in ui
    assert "view?.can_complete_missing" in ui
    assert "view?.completable_fields" in ui
    assert "!present(original(key))&&!present(current(key))" in ui
    assert "view?.assessment_fields" in ui
    assert "view?.can_secondary_review" in ui
    assert "secondFullReview(" in ui
    assert "reportDataError(" in ui
    assert "SOURCE_CONFIRMED" in ui
    assert "UNAVAILABLE" in ui
    assert "gate1-raw-original" in ui
    assert "engagement_likes" in TECHNICAL_READ_ONLY_FIELDS
    assert "candidate_names" in ASSESSMENT_FIELDS
    assert "incident_jurisdiction" in SENSITIVE
    assert "canonical_url" in COMPLETABLE_FIELDS
    assert "canonical_url" in FIELDS


def test_writes_retain_expected_revision_provenance_and_no_training():
    ui=UI_PATH.read_text()
    backend=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    for marker in ("expected_revision:view.revision", "expected_assessment_id:detail.assessment_id",
                   "expected_source_digest:detail.source_integrity_digest",
                   "base44.inboxHumanReview.saveFullReview(", "base44.inboxHumanReview.correct(",
                   "await reload()", "onSaved?.()"):
        assert marker in ui,marker
    for marker in ('"qa_audit_only":True','"original_source_preserved":True',
                   '"canonical_assessment_preserved":True',
                   '"official_insight_published":False','"model_training_triggered":False'):
        assert marker in backend,marker
