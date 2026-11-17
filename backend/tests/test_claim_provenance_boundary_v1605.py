"""v160.5: formal-only social provenance does not demand an unrelated law PDF."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def assessment(answer,question="Summarize social monitoring posts"):
    evidence=[{"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
               "source_excerpt":"An unverified allegation circulating in public posts."}]
    visible,cited,ground=audit_assistant_answer(
        question,evidence,answer,profile="SOCIAL_ANALYSIS",language="en")
    return evaluate_answer_quality(question,evidence,visible,cited,
                                   profile="SOCIAL_ANALYSIS",grounding=ground)

def test_social_only_formal_assertion_triggers_specific_source_review_not_missing_law():
    q=assessment("BAWASLU confirmed an electoral violation [SOCIAL-1].")
    codes=[x["code"] for x in q["legal_review_summary"]["issues"]]
    assert "FORMAL_OUTCOME_SOCIAL_ONLY" in codes
    assert "ELIGIBLE_LEGAL_SOURCE_MISSING" not in codes
    assert q["formal_outcome_source_provenance"]["formal_decision_verified"] is False

def test_actual_legal_question_still_requires_legal_citation():
    q=assessment("BAWASLU confirmed an electoral violation [SOCIAL-1].",
                 question="What legal regulation applies?")
    codes=[x["code"] for x in q["legal_review_summary"]["issues"]]
    assert "FORMAL_OUTCOME_SOCIAL_ONLY" in codes
    assert "ELIGIBLE_LEGAL_SOURCE_MISSING" in codes

def test_contextual_report_not_reviewed_as_formal_decision():
    q=assessment("A public post claims there may be a violation [SOCIAL-1].")
    assert q["formal_outcome_source_provenance"]["review_required_count"]==0
    assert q["legal_review_summary"]["applicable"] is False
