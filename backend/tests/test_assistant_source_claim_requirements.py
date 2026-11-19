"""Adversarial source-claim checks for offline response QA (no provider calls)."""
import pytest
from app.assistant_source_claim_requirements import check_source_claim_requirements as check


def pdf(source="Petugas wajib verifikasi lokasi kejadian."):
    return [{"record_id":"DOC-1-P8", "record_type":"PDF_KNOWLEDGE",
             "source_excerpt":source}]


def req(anchor="wajib verifikasi lokasi kejadian", polarity="POSITIVE"):
    return [{"source_id":"DOC-1-P8","anchor":anchor,"expected_polarity":polarity}]


@pytest.mark.parametrize("answer,ids,reason", [
    ("Petugas tidak wajib verifikasi lokasi kejadian [DOC-1-P8].",
     ["DOC-1-P8"],"EXPLICIT_POLARITY_REVERSAL"),
    ("Petugas wajib verifikasi lokasi kejadian.", [],
     "NO_LOCALLY_CITED_ANCHOR"),
    ("Petugas wajib verifikasi lokasi kejadian [DOC-9-P2].",
     ["DOC-9-P2"],"NO_LOCALLY_CITED_ANCHOR"),
    ("Petugas wajib verifikasi lokasi kejadian [DOC-1-P8]. "
     "Namun petugas tidak wajib verifikasi lokasi kejadian [DOC-1-P8].",
     ["DOC-1-P8"],"CONFLICTING_LOCAL_CLAIMS"),
    ("Petugas wajib verifikasi lokasi kejadian [DOC-1-P8]. "
     "Pengawasan berbeda di provinsi lain.",
     [],"NO_LOCALLY_CITED_ANCHOR"),
])
def test_detects_known_source_requirement_failures(answer, ids, reason):
    result=check(answer,req(),pdf(),ids)
    assert result["status"]=="REVIEW_REQUIRED"
    assert result["review_items"][0]["reason"]==reason
    assert result["model_answer_accuracy"] is None


def test_passing_literal_reference_does_not_claim_truth():
    result=check("Petugas wajib verifikasi lokasi kejadian [DOC-1-P8].",
                 req(),pdf(),["DOC-1-P8"])
    assert result["status"]=="PASS_NARROW_LEXICAL_ONLY"
    assert result["semantic_entailment_verified"] is False
    assert result["human_accuracy"] is None


def test_local_standalone_next_line_citation_is_allowed():
    result=check("Petugas wajib verifikasi lokasi kejadian.\n[DOC-1-P8]",
                 req(),pdf(),["DOC-1-P8"])
    assert result["status"]=="PASS_NARROW_LEXICAL_ONLY"


def test_source_missing_expected_phrase_never_passes():
    result=check("Petugas wajib verifikasi lokasi kejadian [DOC-1-P8].",
                 req(),pdf("Sumber lain yang tidak menyatakan kewajiban."),["DOC-1-P8"])
    assert result["review_items"][0]["reason"]=="ANCHOR_NOT_IN_SELECTED_SOURCE"


def test_explicit_negative_source_and_answer_agree():
    result=check("Petugas tidak wajib verifikasi lokasi kejadian [DOC-1-P8].",
                 req(polarity="NEGATIVE"),
                 pdf("Petugas tidak wajib verifikasi lokasi kejadian."),
                 ["DOC-1-P8"])
    assert result["status"]=="PASS_NARROW_LEXICAL_ONLY"


def test_unsupported_requirement_is_invalid():
    result=check("Petugas wajib verifikasi lokasi kejadian [DOC-1-P8].",
                 [{"source_id":"DOC-1-P8","anchor":"wajib verifikasi lokasi kejadian",
                   "expected_polarity":"OTHER"}],pdf(),["DOC-1-P8"])
    assert result["review_items"][0]["reason"]=="INVALID_REQUIREMENT"


def test_two_opposing_mentions_in_same_locally_cited_sentence():
    result=check(
        "Petugas wajib verifikasi lokasi kejadian tetapi petugas tidak wajib verifikasi lokasi kejadian [DOC-1-P8].",
        req(),pdf(),["DOC-1-P8"])
    assert result["status"]=="REVIEW_REQUIRED"
    assert result["review_items"][0]["reason"]=="CONFLICTING_LOCAL_CLAIMS"


def test_repeated_matching_mentions_do_not_create_false_conflict():
    result=check(
        "Petugas wajib verifikasi lokasi kejadian; tim nasional wajib verifikasi lokasi kejadian [DOC-1-P8].",
        req(),pdf(),["DOC-1-P8"])
    assert result["status"]=="PASS_NARROW_LEXICAL_ONLY"


def test_cited_wrong_record_cannot_authorize_source_requirement():
    records=pdf()+[{"record_id":"DOC-2-P8","record_type":"PDF_KNOWLEDGE",
                    "source_excerpt":"Dokumen berbeda."}]
    result=check("Petugas wajib verifikasi lokasi kejadian [DOC-2-P8].",
                 req(),records,["DOC-2-P8"])
    assert result["status"]=="REVIEW_REQUIRED"
    assert result["review_items"][0]["reason"]=="NO_LOCALLY_CITED_ANCHOR"
