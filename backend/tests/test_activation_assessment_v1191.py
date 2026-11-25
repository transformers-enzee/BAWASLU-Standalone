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


def test_ai_budget_diagnostics_distinguish_unconfigured_and_exhausted(monkeypatch):
    from app.activation_assessment import remaining_budget,budget_blocker_message
    from app.db import Base,engine,SessionLocal
    Base.metadata.create_all(engine)
    db=SessionLocal()
    try:
        for key in ("OPENAI_API_KEY","BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN","BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN","BAWASLU_AI_ASSESSMENTS_PER_RUN"):
            monkeypatch.delenv(key,raising=False)
        b=remaining_budget(db,987654)
        assert "AI_PROVIDER_NOT_CONFIGURED" in b["blockers"]
        assert "DAILY_LIMIT_NOT_CONFIGURED" in b["blockers"]
        assert "LIFETIME_LIMIT_NOT_CONFIGURED" in b["blockers"]
        assert "PER_RUN_LIMIT_NOT_CONFIGURED" in b["blockers"]
        assert b["available"]==0
        assert "not configured" in budget_blocker_message(b)
        monkeypatch.setenv("OPENAI_API_KEY","mock-test-key")
        monkeypatch.setenv("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN","12")
        monkeypatch.setenv("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN","24")
        monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","6")
        b=remaining_budget(db,987654)
        assert b["available"]==12 and b["per_run"]==6
        assert "DAILY_LIMIT_NOT_CONFIGURED" not in b["blockers"]
    finally:db.close()
