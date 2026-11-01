"""Activation assessment regression: source labels, budgets and durable progress."""
from types import SimpleNamespace
from app.activation_assessment import needs_full_assessment


def test_provider_preliminary_relevance_is_not_complete_intelligence_assessment():
    for model in ("PRISM_PENDING_OPENAI", "PRISM_OPENAI_TOPIC_CLASSIFIER"):
        assessment=SimpleNamespace(model_version=model,relevance_label="RELEVANT")
        assert needs_full_assessment(assessment)


def test_successful_full_screen_not_billed_again():
    record=SimpleNamespace(model_version="gpt-4o-mini",relevance_label="IRRELEVANT")
    assert not needs_full_assessment(record)
    record.relevance_label="RELEVANT"
    assert not needs_full_assessment(record)


def test_unassessed_model_still_requires_full_screen():
    assert needs_full_assessment(None)
    assert needs_full_assessment(SimpleNamespace(model_version="gpt-4o-mini",
                                                 relevance_label="UNASSESSED"))


def test_activate_uses_full_assessment_not_duplicate_topic_only_ai_pass():
    from pathlib import Path
    import app.prism_discover as prism
    source=Path(prism.__file__).read_text()
    assert "full_assessment=True" in source
    assert "if not full_assessment:" in source
    assert "execute_run(run.id)" in source
    assert "assessment_result_ids" in source


def test_persistent_status_and_partial_budget_controls_are_present():
    from pathlib import Path
    from app import activation_assessment
    source=Path(activation_assessment.__file__).read_text()
    assert "assessment_worker_complete" in source
    assert "reserve" not in source.lower() or "budget" in source.lower()
    assert "if not budget[\"available\"]" in source
    assert "if not needs_full_assessment(previous)" in source


def test_dashboard_omits_unscreened_prism_preliminary_from_inbox():
    from pathlib import Path
    import app.campaigns as campaigns
    source=Path(campaigns.__file__).read_text()
    assert "preliminary=bool(assessment and assessment.model_version=='PRISM_PENDING_OPENAI')" in source
    assert "if preliminary or not assessment" in source
