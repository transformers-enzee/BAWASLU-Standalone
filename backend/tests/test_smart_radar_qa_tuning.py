"""Continuous prompt calibration must never train on sealed final holdouts."""
import pytest
from pydantic import ValidationError
from app.smart_radar_qa_tuning import (
    DEFAULT_INSTRUCTIONS, SYSTEM_GUARD, version_key, SavePrompt, RunPrompt)
from app.smart_radar_qa import CAT_SET

def test_default_covers_all_seven_categories():
    assert all(category.lower() in DEFAULT_INSTRUCTIONS.lower() for category in CAT_SET)
    assert "MAIN COMMUNICATIVE PURPOSE" in DEFAULT_INSTRUCTIONS
    assert "Do not turn a" in DEFAULT_INSTRUCTIONS
    assert "Participatory Oversight" in DEFAULT_INSTRUCTIONS

def test_saved_prompt_minimum_length_and_run_bounds():
    with pytest.raises(ValidationError):
        SavePrompt(title="x",instructions="short")
    with pytest.raises(ValidationError):
        RunPrompt(version_id=1,limit=4)
    assert SavePrompt(title="First QA rubric",
       instructions=DEFAULT_INSTRUCTIONS).instructions==DEFAULT_INSTRUCTIONS

def test_version_names_are_distinct_and_versioned():
    assert version_key(1)=="qa-prompt-tune-v1"
    assert version_key(2)!=version_key(1)

def test_output_guard_demands_source_only_evidence():
    assert "untrusted data" in SYSTEM_GUARD
    assert "original" in SYSTEM_GUARD.lower()

def test_tuning_endpoint_only_targets_development_records():
    import inspect
    from app.smart_radar_qa_tuning import run_tuning
    source=inspect.getsource(run_tuning)
    assert 'r["cohort"]=="development"' in source
    assert 'r["cohort"]=="exemplar"' in source
    assert "sealed_holdout" not in source

def test_mismatch_is_completed_not_a_blocker():
    from app.smart_radar_qa_tuning import choose_development_candidates
    dev=[{"qa_id":f"QA-{i}"} for i in range(1,7)]
    # QA-1 is a persisted classification mismatch; QA-2 is a real
    # failed AI request. Neither should trap the next three candidates.
    selected=choose_development_candidates(
        dev,completed={"QA-1"},failures={"QA-2"},retry_failed=False)
    assert [r["qa_id"] for r in selected]==["QA-3","QA-4","QA-5","QA-6"]
    retries=choose_development_candidates(
        dev,completed={"QA-1"},failures={"QA-2"},retry_failed=True)
    assert [r["qa_id"] for r in retries]==["QA-2"]

def test_qa_batch_ignores_daily_and_respects_lifetime(monkeypatch):
    import app.smart_radar_qa_tuning as mod
    monkeypatch.setattr(mod,"qa_readiness",lambda db:{
        "max_run":3,"daily_remaining":None,"lifetime_remaining":17})
    assert mod._available_slots(None,3)==3
    monkeypatch.setattr(mod,"qa_readiness",lambda db:{
        "max_run":3,"daily_remaining":None,"lifetime_remaining":2})
    assert mod._available_slots(None,3)==2
    monkeypatch.setattr(mod,"qa_readiness",lambda db:{
        "max_run":3,"daily_remaining":None,"lifetime_remaining":0})
    assert mod._available_slots(None,3)==0

def test_retry_requires_explicit_selection():
    x=RunPrompt(version_id=6,limit=1,retry_failed=True)
    assert x.retry_failed is True
    assert RunPrompt(version_id=6,limit=3).retry_failed is False
