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
