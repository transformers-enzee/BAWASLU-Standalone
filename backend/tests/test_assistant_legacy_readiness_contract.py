"""Prevent changes to the v148.4 four-check public response contract.

New deterministic probes are supported as additive diagnostics without
reordering legacy readiness checks or misrepresenting claim truth.
"""
from app.assistant_answer_quality import evaluate_answer_quality

CORE = ["citation_grounding", "source_relevance",
        "legal_uncertainty", "cross_module_consistency"]


def test_legacy_core_and_supplemental_diagnostics_are_separate():
    evidence=[{"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
               "source_excerpt":"Riau oversight"}]
    response=evaluate_answer_quality("Riau",evidence,
        "Monitoring notes [SOCIAL-1].",["SOCIAL-1"],
        profile="SOCIAL_ANALYSIS",grounding={})
    assert [entry["id"] for entry in response["checks"]]==CORE
    supplemental={item["id"]:item for item in response["additional_checks"]}
    assert {"citation_inventory_consistency","pdf_quoted_passage_alignment",
            "requested_topic_coverage"}.issubset(supplemental)
    assert response["claim_truth_verified"] is False
    assert response["semantic_entailment_verified"] is False


def test_supplemental_review_is_not_silently_lost():
    evidence=[{"record_id":"DOC-1-P4","record_type":"PDF_KNOWLEDGE",
               "source_excerpt":"This page is about a different subject.",
               "document_type":"SOP","review_status":"UNREVIEWED"}]
    response=evaluate_answer_quality(
        "What does this PDF say?",evidence,
        'The document says “petugas memverifikasi lokasi kejadian” [DOC-1-P4].',
        ["DOC-1-P4"],profile="PDF_GUIDANCE",grounding={})
    assert [entry["id"] for entry in response["checks"]]==CORE
    assert "pdf_quoted_passage_alignment" in response["additional_needs_review"]
    assert response["pdf_quoted_passage_alignment"]["status"]=="REVIEW_REQUIRED"
    assert response["human_review_required"] is True


def test_legacy_counts_cover_exactly_the_core_four():
    response=evaluate_answer_quality("Riau",[], "Not enough evidence.",[],
                                      grounding={})
    assert (response["passed_checks"]+response["review_required_checks"]
            +response["not_applicable_checks"])==4


def test_supplemental_warnings_visible_in_consolidated_metadata():
    evidence=[{"record_id":"DOC-1-P4","record_type":"PDF_KNOWLEDGE",
               "source_excerpt":"Unrelated contents of an uploaded page.",
               "document_type":"OTHER","review_status":"UNREVIEWED"}]
    response=evaluate_answer_quality(
        "Explain this PDF",evidence,
        'The page says “petugas memverifikasi lokasi kejadian” [DOC-1-P4].',
        ["DOC-1-P4"],profile="PDF_GUIDANCE",grounding={})
    assert response["supplemental_review_required"] is True
    assert response["supplemental_review_count"] >= 1
    assert "pdf_quoted_passage_alignment" in response["all_readiness_review_reasons"]
    assert "pdf_quoted_passage_alignment" not in [check["id"] for check in response["checks"]]
    assert response["claim_truth_verified"] is False


def test_consolidated_reasons_have_no_duplicates_and_keep_core_separate():
    evidence=[{"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
               "source_excerpt":"Riau oversight"}]
    response=evaluate_answer_quality("Riau",evidence,
        "No selected citation.",[],profile="SOCIAL_ANALYSIS",grounding={})
    combined=response["all_readiness_review_reasons"]
    assert len(combined)==len(set(combined))
    assert set(response["needs_review"]).issubset(combined)
    assert set(response["additional_needs_review"]).issubset(combined)
    assert response["review_required_checks"] == sum(
        check["status"]=="REVIEW_REQUIRED" for check in response["checks"])
