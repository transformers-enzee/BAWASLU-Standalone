"""v187.4 selective officer review contracts: six assessment areas and data-error reporting."""
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.inbox_human_full_review_v1868 import (
    ASSESSMENT_FIELDS, SOURCE_EXCEPTION_FIELDS, TECHNICAL_READ_ONLY_FIELDS,
    REPORTABLE_FIELDS, FIELDS, SourceErrorIn, SOURCE_ERROR_ACTION,
)
from app.inbox_gate1_quality_hints_v1871 import quality_hints

ROOT = Path(__file__).resolve().parents[2]


def test_six_review_areas_do_not_include_provider_metrics():
    assert ASSESSMENT_FIELDS == {
        "relevance", "sentiment", "candidate_names", "political_parties",
        "topic_labels", "narrative", "potential_issue_categories", "evidence_quality"
    }
    assert SOURCE_EXCEPTION_FIELDS.isdisjoint(TECHNICAL_READ_ONLY_FIELDS)
    assert ASSESSMENT_FIELDS.isdisjoint(TECHNICAL_READ_ONLY_FIELDS)
    assert {"engagement_likes", "engagement_shares", "engagement_comments",
            "engagement_views", "transcript", "translation"} <= TECHNICAL_READ_ONLY_FIELDS
    assert {"platform","author_name","canonical_url","published_at"} <= SOURCE_EXCEPTION_FIELDS
    assert REPORTABLE_FIELDS <= FIELDS
    assert SOURCE_ERROR_ACTION == "GATE1_QA_SOURCE_ERROR_REPORTED"


def test_missing_candidate_or_location_does_not_generate_error_hint():
    src = type("Source", (), {"canonical_url":"https://www.youtube.com/watch?v=123"})()
    hints = quality_hints({
        "platform":{"effective":"youtube"},
        "canonical_url":{"effective":src.canonical_url},
        "country":{"effective":""}, "candidate_names":{"effective":""},
    },src)
    assert hints == []


def test_source_error_contract_requires_snapshot_and_excludes_invalid_field():
    with pytest.raises(ValidationError):
        SourceErrorIn(field="transcript",expected_assessment_id=0,expected_source_digest="0"*64)
    with pytest.raises(ValidationError):
        SourceErrorIn(field="transcript",expected_assessment_id=1,expected_source_digest="bad")
    assert SourceErrorIn(field="transcript",expected_assessment_id=1,expected_source_digest="a"*64).note==""


def test_officer_ui_no_long_field_selector_for_routine_review():
    source=(ROOT/"frontend/src/components/intel/Gate1FullWorkbench.jsx").read_text()
    assert "const ASSESSMENT_GROUPS=[" in source
    assert source.count("idLabel:") == 6
    assert "gate1-review-group-" in source
    assert "gate1-quick-field-select" in source
    assert "Missing values are reviewed only when relevant" in source
    assert "TECHNICAL_READ_ONLY_FIELDS.map" in source
    assert "gate1-readonly-technical" in source
    assert "gate1-readonly-source" in source
    assert "gate1-data-error-form" in source
    assert "gate1-open-source-override" in source
    assert "view.can_correct_source" in source
    assert "sourceErrorOpen" in source
    assert "base44.inboxHumanReview.reportDataError(" in source
    assert "fieldFilter" not in source
    assert "Missing values (" not in source
    assert "TECHNICAL_READ_ONLY_FIELDS.includes(field)" not in source
    api=(ROOT/"frontend/src/api/base44Client.js").read_text()
    assert "reportDataError:" in api
    backend=(ROOT/"backend/app/inbox_human_full_review_v1868.py").read_text()
    assert 'if field not in ASSESSMENT_FIELDS and not has(officer,"administration")' in backend
    assert '"source_overridden":False' in backend
    assert '"official_intelligence_published":False' in backend
