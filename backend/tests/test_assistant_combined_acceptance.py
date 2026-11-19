"""Offline end-to-end acceptance for combined Assistant quality diagnostics.

Synthetic evidence only: no database, network, OpenAI calls or live officer data.
Passing means warnings and references are tracked consistently, NOT that AI
answers are accurate or that any source is legally authoritative.
"""
from app.assistant_answer_quality import evaluate_answer_quality

CORE = ["citation_grounding", "source_relevance",
        "legal_uncertainty", "cross_module_consistency"]


def source(ref, record_type, excerpt, document_type=None):
    return {"record_id": ref, "record_type": record_type,
            "source_excerpt": excerpt, "document_type": document_type,
            "review_status": "UNREVIEWED"}


def quality(question, evidence, answer, ids, profile="PDF_GUIDANCE"):
    return evaluate_answer_quality(
        question, evidence, answer, ids, profile=profile, grounding={})


def test_wrong_pdf_quote_is_in_unified_review_reasons():
    evidence=[source("DOC-1-P8", "PDF_KNOWLEDGE",
                     "A verified location must be recorded.", "SOP")]
    response=quality("Jelaskan penugasan.",evidence,
        'Dokumen menyebut “petugas menetapkan pelanggaran hukum” [DOC-1-P8].',
        ["DOC-1-P8"])
    assert response["pdf_quoted_passage_alignment"]["status"]=="REVIEW_REQUIRED"
    assert "pdf_quoted_passage_alignment" in response["all_readiness_review_reasons"]
    assert response["supplemental_review_required"] is True
    assert response["claim_truth_verified"] is False


def test_question_coverage_warning_surfaces_without_legacy_check_changes():
    evidence=[source("DOC-1-P8", "PDF_KNOWLEDGE",
                     "Penugasan hanya sesudah verifikasi.", "SOP")]
    response=quality("Jelaskan penugasan dan pembatasan akses pengguna.",
        evidence,"Penugasan memerlukan verifikasi [DOC-1-P8].",["DOC-1-P8"])
    assert response["requested_topic_coverage"]["status"]=="NEEDS_REVIEW"
    assert "requested_topic_coverage" in response["all_readiness_review_reasons"]
    assert [entry["id"] for entry in response["checks"]]==CORE


def test_formal_decision_social_post_is_never_verified():
    evidence=[source("SOCIAL-1", "SOCIAL_LISTENING",
                     "A public post alleges an irregularity")]
    response=quality("Ringkas unggahan.", evidence,
        "BAWASLU telah menetapkan pelanggaran. [SOCIAL-1]",
        ["SOCIAL-1"],profile="CROSS_MODULE_REVIEW")
    provenance=response["formal_outcome_source_provenance"]
    assert provenance["status"]=="REVIEW_REQUIRED"
    assert provenance["review_items"][0]["reason"]=="FORMAL_DECISION_CITED_ONLY_TO_SOCIAL_POSTS"
    assert provenance["formal_decision_verified"] is False
    assert response["legal_verdict_confirmed"] is False


def test_categorical_platform_claim_not_verified_by_social_post():
    evidence=[source("SOCIAL-4", "SOCIAL_LISTENING",
                     "Platform user speculation")]
    response=quality("Review social post.",evidence,
        "Unggahan TikTok melanggar kebijakan platform. [SOCIAL-4]",
        ["SOCIAL-4"],profile="SOCIAL_ANALYSIS")
    check=response["platform_policy_legal_boundary"]
    assert check["status"]=="REVIEW_REQUIRED"
    assert check["platform_breach_confirmed"] is False
    assert check["review_items"][0]["reason"]=="PLATFORM_VERDICT_WITHOUT_VERIFIED_PROVIDER_DECISION"


def test_citation_inventory_disagreement_never_counts_as_verified():
    evidence=[source("DOC-1-P8","PDF_KNOWLEDGE",
                     "Source text here.", "GUIDANCE"),
              source("DOC-1-P9","PDF_KNOWLEDGE",
                     "Another page text.", "GUIDANCE")]
    response=quality("Explain PDF.",evidence,
        "See page [DOC-1-P8] and [DOC-1-P9].",["DOC-1-P8"])
    assert response["citation_inventory_consistency"]["status"]=="REVIEW_REQUIRED"
    assert response["citation_inventory_consistency"]["displayed_not_in_metadata"]==["DOC-1-P9"]
    assert "citation_inventory_consistency" in response["all_readiness_review_reasons"]
    assert response["semantic_entailment_verified"] is False


def test_empty_evidence_does_not_generate_false_assurance():
    response=quality("Jelaskan bukti.",[],"Tidak ada bukti.",[],
                     profile="SOCIAL_ANALYSIS")
    assert len(response["checks"])==4
    assert response["human_review_required"] is True
    assert response["claim_truth_verified"] is False
    assert response["human_accuracy"] is None
