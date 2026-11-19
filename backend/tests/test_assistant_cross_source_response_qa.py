"""Cross-source Assistant benchmark: 32 synthetic multi-paragraph QA cases.

This exercises deterministic warning detection using mock source excerpts.
It never invokes a model or represents measured accuracy of model responses.
"""
import json
from collections import Counter
from pathlib import Path
import pytest
from app.assistant_source_claim_requirements import check_source_claim_requirements

ROOT=Path(__file__).parent/"fixtures"
CASES=json.loads((ROOT/"assistant_cross_source_reasoning_cases.json").read_text(
    encoding="utf-8"))["cases"]


def test_cross_source_inventory_and_adversarial_balance():
    assert len(CASES)==32
    assert len({item["id"] for item in CASES})==32
    assert len({item["topic"] for item in CASES})==8
    assert Counter(item["variant"] for item in CASES)=={
        "COMPLETE_TWO_SOURCES":8,"MISSING_SECOND_CLAIM":8,
        "WRONG_SECOND_CITATION":8,"FIRST_CLAIM_REVERSED":8}
    assert all(item["synthetic_only"] for item in CASES)


@pytest.mark.parametrize("case",CASES,ids=lambda case:case["id"])
def test_cross_source_answer_detects_known_defect(case):
    source_check=check_source_claim_requirements(
        case["candidate_answer"],case["requirements"],
        case["authorized_evidence"],case["candidate_citation_ids"])
    assert source_check["status"]==case["expected_status"]
    if case["expected_issue"]:
        assert any(item["reason"]==case["expected_issue"]
                   for item in source_check["review_items"])
    else:
        assert source_check["review_items"]==[]
    assert source_check["requirement_count"]==2
    assert source_check["model_answer_accuracy"] is None
    assert source_check["source_truth_verified"] is False
    assert source_check["model_calls"]==0


def test_wrong_page_does_not_leak_another_page_authority():
    case=next(item for item in CASES if
              item["variant"]=="WRONG_SECOND_CITATION" and
              item["topic"]=="authority_vs_location")
    result=check_source_claim_requirements(
        case["candidate_answer"],case["requirements"],
        case["authorized_evidence"],case["candidate_citation_ids"])
    assert result["review_items"][0]["source_id"]=="DOC-42-P2"
    assert result["review_items"][0]["reason"]=="NO_LOCALLY_CITED_ANCHOR"
