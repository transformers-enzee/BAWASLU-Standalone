"""v187.1 contextual Gate 1: deterministic hints, protected values, and low-friction review."""
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from app.inbox_gate1_quality_hints_v1871 import platform_from_url, quality_hints
from app.inbox_human_full_review_v1868 import _value

ROOT = Path(__file__).resolve().parents[2]


def test_url_detection_avoids_similar_lookalike_domains():
    assert platform_from_url("https://www.youtube.com/watch?v=123") == "youtube"
    assert platform_from_url("https://youtu.be/abc") == "youtube"
    assert platform_from_url("https://m.facebook.com/post/123") == "facebook"
    assert platform_from_url("https://youtube.com.evil.example/post") == ""
    assert platform_from_url("javascript:alert(1)") == ""


def test_mapping_warnings_do_not_change_effective_values():
    src = SimpleNamespace(canonical_url="https://youtube.com/watch?v=abc")
    fields = {
        "platform": {"effective": "@bimaputrachannel"},
        "canonical_url": {"effective": src.canonical_url},
        "province": {"effective": "youtube"},
    }
    hints = quality_hints(fields, src)
    assert {h["code"] for h in hints} == {
        "POSSIBLE_PLATFORM_MAPPING_ERROR", "POSSIBLE_GEOGRAPHY_MAPPING_ERROR"
    }
    assert next(h for h in hints if h["field"] == "platform")["suggested_value"] == "youtube"
    assert next(h for h in hints if h["field"] == "province")["suggested_value"] == ""
    assert fields["platform"]["effective"] == "@bimaputrachannel"
    assert fields["province"]["effective"] == "youtube"
    assert quality_hints({"platform": {"effective": "youtube"}, "province": {"effective": ""}}, src) == []


def test_replacement_validation_rejects_handle_platform_or_platform_geo():
    assert _value("platform", "youtube") == "youtube"
    with pytest.raises(HTTPException):
        _value("platform", "@account")
    with pytest.raises(HTTPException):
        _value("province", "youtube")
    with pytest.raises(HTTPException):
        _value("country", "@account")


def test_contextual_workbench_and_governance_contracts():
    ui = (ROOT / "frontend/src/components/intel/Gate1FullWorkbench.jsx").read_text()
    for name in ("gate1-current-effective-value", "gate1-field-filter",
                 "gate1-sensitive-reason", "gate1-complete-missing-field",
                 "Complete Missing Data", "gate1-no-material-missing"):
        assert name in ui
    assert "gate1-contextual-missing-tasks" in ui
    assert "correctionReason" in ui
    assert "View all values and audit history" in ui
    assert "gate1-secondary-review" in ui
    backend = (ROOT / "backend/app/inbox_human_full_review_v1868.py").read_text()
    assert '"quality_hints":quality_hints(p["fields"],source)' in backend
    assert '"qa_audit_only":True' in backend
    assert "official_insight_published" in backend
