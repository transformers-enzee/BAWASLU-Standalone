"""Second half of the priority 100-case Assistant benchmark, no API calls."""
import json
from pathlib import Path
import pytest
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality
from app.assistant_source_claim_requirements import check_source_claim_requirements
from app.assistant_response_benchmark import check_required_answer_points

ROOT=Path(__file__).parent / "fixtures"
P1=json.loads((ROOT/"assistant_response_benchmark_p1.json").read_text(encoding="utf-8"))
P2=json.loads((ROOT/"assistant_response_benchmark_p2.json").read_text(encoding="utf-8"))
CASES=P2["cases"]


def test_priority_benchmark_contains_100_independent_synthetic_cases():
    combined=P1["cases"]+P2["cases"]
    assert len(combined)==100
    assert len({case["id"] for case in combined})==100
    expected={"PDF_SOP":30,"LEGAL":20,"INBOX":15,"SOCIAL":15,"CROSS":10,"FOLLOWUP":10}
    assert {kind:sum(case["category"]==kind for case in combined)
            for kind in expected} == expected
    assert all(case["synthetic_only"] for case in combined)


@pytest.mark.parametrize("case",CASES,ids=lambda case:case["id"])
def test_second_batch_candidate_answer_review(case):
    answer,cited,ground=audit_assistant_answer(
        case["question"],case["authorized_evidence"],
        case["candidate_answer"],case["candidate_citation_ids"],
        profile=case["profile"],language=case["language"])
    quality=evaluate_answer_quality(
        case["question"],case["authorized_evidence"],answer,cited,
        profile=case["profile"],grounding=ground)
    criterion=check_required_answer_points(answer,case["required_answer_points"])
    expected=case["expected_detection"]
    assert quality["human_accuracy"] is None
    assert criterion["accuracy_score"] is None
    assert quality["claim_truth_verified"] is False
    if expected=="SUPPORTED_CITED":
        requirements=[{"source_id":case["authorized_evidence"][0]["record_id"],
                       "anchor":point}
                      for point in case["required_answer_points"]]
        support=check_source_claim_requirements(
            answer,requirements,case["authorized_evidence"],cited)
        assert support["status"]=="PASS_NARROW_LEXICAL_ONLY"
        assert support["semantic_entailment_verified"] is False

        assert cited
        assert criterion["status"]=="PASS_LEXICAL_ONLY"
    elif expected=="MISSING_CITATION":
        assert cited==[]
        assert quality["checks"][0]["status"]=="REVIEW_REQUIRED"
    elif expected=="UNKNOWN_CITATION":
        assert ground["rejected_unavailable_citations"]>=1
        assert cited==[]
    elif expected=="ANSWER_OMITS_REQUIRED_POINT":
        assert criterion["status"]=="NEEDS_REVIEW"
        assert criterion["missing_points"]
    elif expected=="QUOTE_NOT_IN_SOURCE":
        assert quality["pdf_quoted_passage_alignment"]["status"]=="REVIEW_REQUIRED"
    else:
        raise AssertionError(f"Unexpected case {expected}")


def test_required_point_rubric_is_lexical_not_a_truth_claim():
    result=check_required_answer_points("tidak wajib verifikasi lokasi",["wajib verifikasi lokasi"])
    assert result["status"]=="PASS_LEXICAL_ONLY"
    assert result["semantic_entailment_verified"] is False
    assert result["human_scoring_completed"] is False
