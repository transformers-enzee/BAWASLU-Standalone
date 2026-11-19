"""Phase-one response-quality benchmark: 50 synthetic PDF/SOP/legal cases.

These fixtures challenge actual deterministic reply validators using candidate
answers. They are not fresh LLM generations, officer scoring, real legal
references or estimates of the Assistant's production answer accuracy.
"""
import json
from pathlib import Path
import pytest
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

FIXTURE = Path(__file__).parent / "fixtures" / "assistant_response_benchmark_p1.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
CASES = DATA["cases"]


def test_benchmark_inventory_and_independent_source_scope():
    assert DATA["case_count"] == 50
    assert len(CASES) == 50
    assert len({case["id"] for case in CASES}) == 50
    assert sum(case["category"] == "PDF_SOP" for case in CASES) == 30
    assert sum(case["category"] == "LEGAL" for case in CASES) == 20
    assert len({case["topic"] for case in CASES}) >= 10
    assert {case["expected_detection"] for case in CASES} == {
        "PASS", "MISSING_CITATION", "UNAUTHORIZED_CITATION",
        "QUOTATION_MISMATCH", "UNSUPPORTED_FORMAL_OUTCOME"}
    for case in CASES:
        assert case["synthetic_only"] is True
        assert case["required_answer_points"]
        assert case["authorized_evidence"]
        assert all(row["record_type"] == "PDF_KNOWLEDGE"
                   for row in case["authorized_evidence"])


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_synthetic_question_to_response_integrity(case):
    visible, cited, grounding = audit_assistant_answer(
        case["question"], case["authorized_evidence"],
        case["candidate_answer"], case["candidate_citation_ids"],
        profile=case["profile"], language=case["language"])
    qa = evaluate_answer_quality(
        case["question"], case["authorized_evidence"],
        visible, cited, profile=case["profile"], grounding=grounding)
    expected = case["expected_detection"]
    authorized = {row["record_id"] for row in case["authorized_evidence"]}
    assert set(cited).issubset(authorized)
    assert qa["human_accuracy"] is None
    assert qa["claim_truth_verified"] is False
    assert qa["semantic_entailment_verified"] is False
    assert qa["legal_currentness_verified"] is False
    if expected == "PASS":
        assert cited
        assert all(point.casefold() in visible.casefold()
                   for point in case["required_answer_points"])
        assert qa["citation_inventory_consistency"]["status"] == "PASS_IDENTIFIERS_ONLY"
    elif expected == "MISSING_CITATION":
        assert not cited
        assert qa["checks"][0]["status"] == "REVIEW_REQUIRED"
    elif expected == "UNAUTHORIZED_CITATION":
        assert grounding["rejected_unavailable_citations"] >= 1
        assert not cited
    elif expected == "QUOTATION_MISMATCH":
        assert qa["pdf_quoted_passage_alignment"]["status"] == "REVIEW_REQUIRED"
        assert "pdf_quoted_passage_alignment" in qa["all_readiness_review_reasons"]
    elif expected == "UNSUPPORTED_FORMAL_OUTCOME":
        assert qa["formal_outcome_source_provenance"]["status"] == "REVIEW_REQUIRED"
        assert qa["formal_outcome_source_provenance"]["formal_decision_verified"] is False
    else:
        raise AssertionError(f"Unexpected case: {expected}")
