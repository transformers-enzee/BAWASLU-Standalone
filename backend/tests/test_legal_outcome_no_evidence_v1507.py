"""v150.7: no-evidence categorical legal decisions require human review."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def test_definite_legal_outcome_without_evidence_is_not_accepted():
    answer,cited,meta=audit_assistant_answer(
        "Summarize the case",[],
        "The officer has been convicted.",profile="SOCIAL_ANALYSIS",language="en")
    qa=evaluate_answer_quality(
        "Summarize the case",[],answer,cited,profile="SOCIAL_ANALYSIS",grounding=meta)
    legal=next(x for x in qa["checks"] if x["id"]=="legal_uncertainty")
    assert meta["human_review_required"] is True
    assert meta["legal_categorical_outcome_needs_officer_review"] is True
    assert legal["status"]=="REVIEW_REQUIRED"
    assert "Legal certainty caution" in answer
    assert meta["legal_verdict_confirmed"] is False

def test_no_evidence_neutral_answer_does_not_force_human_verdict_review():
    answer,cited,meta=audit_assistant_answer(
        "Explain the process",[],"No relevant saved evidence is available.",
        profile="SOCIAL_ANALYSIS",language="en")
    assert meta["human_review_required"] is False
    assert meta["legal_categorical_outcome_flags"]==[]
    assert meta["audit_used_paid_provider"] is False
