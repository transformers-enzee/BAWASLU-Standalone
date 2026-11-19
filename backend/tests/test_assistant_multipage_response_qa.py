"""Two-page, multi-paragraph source-answer evaluation without model calls.

Fixtures are synthetic. Both expected source claims must be present and locally
attributed. This is a narrow heuristic, never proof of legal or factual truth.
"""
import json
from pathlib import Path
import pytest

from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality
from app.assistant_source_claim_requirements import check_source_claim_requirements

DATA=json.loads((Path(__file__).parent/"fixtures"/"assistant_multipage_answer_cases.json")
                .read_text(encoding="utf-8"))
CASES=DATA["cases"]


def test_multipage_inventory_is_bounded_and_has_negative_cases():
    assert len(CASES)==12
    assert len({case["id"] for case in CASES})==12
    assert len({case["topic"] for case in CASES})==3
    assert all(case["synthetic_only"] for case in CASES)
    assert {case["variant"] for case in CASES}=={
        "COMPLETE_TWO_CITATIONS", "OMITTED_SECOND_REQUIREMENT",
        "SECOND_CLAIM_WRONG_PAGE","FIRST_CLAIM_NEGATED"}
    for case in CASES:
        assert len(case["documents"])==2
        assert len(case["requirements"])==2
        assert {item["source_id"] for item in case["requirements"]}=={
            item["record_id"] for item in case["documents"]}


@pytest.mark.parametrize("case",CASES,ids=lambda case:case["id"])
def test_each_source_requirement_is_locally_supported(case):
    visible,cited,ground=audit_assistant_answer(
        case["question"],case["documents"],case["candidate_answer"],
        case["candidate_citation_ids"],profile="PDF_GUIDANCE",language="id")
    evaluated=evaluate_answer_quality(
        case["question"],case["documents"],visible,cited,
        profile="PDF_GUIDANCE",grounding=ground)
    source_check=check_source_claim_requirements(
        visible,case["requirements"],case["documents"],cited)
    assert source_check["status"]==case["expected_status"]
    if case["expected_issue"]:
        assert any(issue["reason"]==case["expected_issue"]
                   for issue in source_check["review_items"])
    else:
        assert not source_check["review_items"]
        assert len(cited)==2
    assert evaluated["human_accuracy"] is None
    assert evaluated["claim_truth_verified"] is False
    assert evaluated["semantic_entailment_verified"] is False
    assert source_check["model_calls"]==0
