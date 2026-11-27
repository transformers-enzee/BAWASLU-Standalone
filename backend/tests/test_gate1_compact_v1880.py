"""BAWASLU v188.0: concise officer variables, retained audit and QA-only authorizations."""
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.inbox_human_full_review_v1868 import (
    _value, INFORMATION_TYPES, FIELDS, ASSESSMENT_FIELDS,
    TECHNICAL_READ_ONLY_FIELDS, SOURCE_EXCEPTION_FIELDS, SENSITIVE
)

ROOT=Path(__file__).resolve().parents[2]
NEW=ROOT/"frontend/src/components/intel/Gate1OfficerValuesV1880.jsx"


def test_information_type_is_validated_and_sensitive_not_provider_data():
    assert "information_type" in FIELDS
    assert "information_type" in ASSESSMENT_FIELDS
    assert "information_type" in SENSITIVE
    assert "information_type" not in SOURCE_EXCEPTION_FIELDS
    assert "information_type" not in TECHNICAL_READ_ONLY_FIELDS
    for value in INFORMATION_TYPES:
        assert _value("information_type",value)==value
    with pytest.raises(HTTPException) as e:
        _value("information_type","CONFIRMED_ELECTORAL_VIOLATION")
    assert e.value.status_code == 422


def test_pilot_mounts_v1880_compact_workbench_and_preserves_legacy():
    parent=(ROOT/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    assert "import Gate1OfficerValuesV1880 from './Gate1OfficerValuesV1880'" in parent
    assert "<Gate1OfficerValuesV1880 campaignId={campaignId} detail={detail}" in parent
    assert "(String(campaignId)==='9'&&detail.qa_audit_only)" in parent
    assert "<Gate1FullWorkbench campaignId={campaignId}" in parent
    assert "gate1-extended-assessment-details" in parent


def test_seven_primary_areas_and_conditional_supporting_values():
    ui=NEW.read_text()
    assert "gate1-officer-values-v1880" in ui
    for item in ("row('relevance')","row('information_type')",
                 "row('potential_issue_categories')","PRIMARY.map(area)"):
        assert item in ui
    assert "PRIMARY=[" in ui
    assert ui.count("label:'")>=4
    for title in ("Involved parties","Incident jurisdiction","Main issue & narrative",
                  "Evidence status"):
        assert title in ui
    assert "showSentiment" in ui and "showChronology" in ui
    assert "gate1-contextual-values" in ui
    assert "gate1-essential-values" in ui
    assert "gate1-area-details-" in ui
    assert "gate1-inline-editor" in ui
    assert "gate1-inline-save" in ui
    assert "Save value" in ui and "Save & Next" in ui
    assert "inboxHumanReview.decide(" not in ui
    assert "Complete Missing Data" not in ui


def test_provider_technical_fields_read_only_until_authorized_override():
    ui=NEW.read_text()
    assert "gate1-source-evidence" in ui
    assert "gate1-provider-metadata" in ui
    assert "gate1-authorized-overrides" in ui
    assert "gate1-all-values-search" in ui
    assert "adminOverride" in ui
    assert "view?.can_correct_source&&adminOverride" in ui
    assert "if(!adminOverride&&sourceKeys.includes(key))return false;" in ui
    assert "if(!adminOverride&&ROUTINE_HIDE.has(key))return false;" in ui
    assert "SOURCE_SUMMARY.map(k=>row(k,{readOnly:!adminOverride}))" in ui
    for f in ("engagement_likes","engagement_shares","engagement_views",
              "relevance_explanation","sentiment_explanation","missing_data",
              "duplicate_reference","provider_fetch_status","officer_notes"):
        assert "'"+f+"'" in ui
    assert "ROUTINE_HIDE" in ui
    assert "gate1-data-error-report" in ui
    assert "reportDataError(" in ui
    assert "Original evidence is preserved" in ui


def test_structured_geography_and_dates_are_readable_without_source_mutation():
    ui=NEW.read_text()
    assert "const formatGeo=" in ui
    assert "const formatDate=" in ui
    assert "'Indonesia'" in ui
    assert "confidence" in ui
    assert "timeZone:'UTC'" in ui
    assert "QA only" in ui
    assert "gate1-raw-original" in ui


def test_secondary_audit_and_optimistic_concurrency_are_retained():
    ui=NEW.read_text()
    for marker in ("expected_revision:view.revision","expected_source_digest:detail.source_integrity_digest",
                   "expected_assessment_id:detail.assessment_id","base44.inboxHumanReview.saveFullReview(",
                   "base44.inboxHumanReview.correct(","secondFullReview(", "view.can_secondary_review",
                   "gate1-variable-audit-history","gate1-secondary-review", "gate1-inline-value",
                   "Previous", "New value", "h.actor_id", "h.fields"):
        assert marker in ui,marker
    backend=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    for marker in ('"qa_audit_only":True','"original_source_preserved":True',
                   '"canonical_assessment_preserved":True','"official_insight_published":False',
                   '"model_training_triggered":False'):
        assert marker in backend,marker
