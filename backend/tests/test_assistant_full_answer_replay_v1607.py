"""12 full-answer synthetic replay cases; never report as real AI accuracy."""
import pytest
from app.assistant_full_answer_replay import (
    CASES,run_full_answer_replay,_social,_formal,CROSS_QUESTION)
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

@pytest.mark.parametrize("case",CASES,ids=lambda x:x["id"])
def test_full_answer_replay_case(case):
    result=run_full_answer_replay((case,))
    assert result["scenarios"]==1
    assert result["cases_matched"]==1,result["results"][0]
    assert result["cases_failed"]==0
    assert result["human_accuracy_measured"] is False
    assert result["human_gold_answers_evaluated"]==0
    assert result["database_writes"]==0
    assert result["paid_ai_calls"]==0
    assert result["real_model_responses_evaluated"]==0

def test_replay_inventory_is_diverse_and_consistent():
    result=run_full_answer_replay()
    assert result["scenarios"]==12
    assert result["cases_matched"]==12
    assert result["cases_failed"]==0
    assert len(result["category_counts"])==12
    assert len({x["id"] for x in result["results"]})==12
    assert all(x["synthetic_only"] for x in result["results"])
    assert result["status"]=="SYNTHETIC_PIPELINE_REGRESSION_ONLY"
    assert result["statistically_representative"] is False
    assert result["formal_client_acceptance_verified"] is False

def test_selected_but_uncited_formal_source_cannot_qualify_as_complete_comparison():
    rows=[_social("SOCIAL-1"),_formal("INT-1")]
    visible,cited,g=audit_assistant_answer(
        CROSS_QUESTION,rows,"A public source [SOCIAL-1].",
        profile="CROSS_MODULE_REVIEW",language="en")
    qa=evaluate_answer_quality(CROSS_QUESTION,rows,visible,cited,
                               profile="CROSS_MODULE_REVIEW",grounding=g)
    cross=next(x for x in qa["checks"] if x["id"]=="cross_module_consistency")
    assert cross["status"]=="REVIEW_REQUIRED"
    assert cross["formal_selected"]==1
    assert cross["formal_cited"]==0
    assert cross["social_cited"]==1
    assert cross["missing_citation_kinds"]==["FORMAL_INTELLIGENCE"]
    assert cross["source_truth_verified"] is False

def test_both_displayed_ids_do_not_imply_truth_or_human_acceptance():
    rows=[_social("SOCIAL-1"),_formal("INT-1")]
    visible,cited,g=audit_assistant_answer(
        CROSS_QUESTION,rows,"A public source [SOCIAL-1]. Inbox case [INT-1].",
        profile="CROSS_MODULE_REVIEW",language="en")
    qa=evaluate_answer_quality(CROSS_QUESTION,rows,visible,cited,
                               profile="CROSS_MODULE_REVIEW",grounding=g)
    cross=next(x for x in qa["checks"] if x["id"]=="cross_module_consistency")
    assert cross["status"]=="PASS"
    assert cross["formal_cited"]==1 and cross["social_cited"]==1
    assert cross["source_truth_verified"] is False
    assert qa["claim_truth_verified"] is False
    assert qa["human_accuracy"] is None
