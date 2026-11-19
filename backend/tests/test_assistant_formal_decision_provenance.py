"""Deterministic, no-API formal-decision provenance regressions."""
import pytest
from app.assistant_claim_provenance import evaluate_claim_provenance


def row(identifier, kind):
    return {"record_id": identifier, "record_type": kind}


@pytest.mark.parametrize("answer,evidence,cited,reason", [
    ("BAWASLU telah menetapkan pelanggaran.", [], [],
     "FORMAL_DECISION_NO_LOCAL_AUTHORIZED_CITATION"),
    ("BAWASLU has officially confirmed an election violation. [SOCIAL-1]",
     [row("SOCIAL-1", "SOCIAL_LISTENING")], ["SOCIAL-1"],
     "FORMAL_DECISION_CITED_ONLY_TO_SOCIAL_POSTS"),
    ("BAWASLU telah menetapkan pelanggaran. [DOC-1-P2]",
     [row("DOC-1-P2", "PDF_KNOWLEDGE")], ["DOC-1-P2"],
     "FORMAL_DECISION_MISSING_FORMAL_RECORD"),
    ("BAWASLU telah menetapkan pelanggaran. [SOCIAL-1] [DOC-1-P2]",
     [row("SOCIAL-1", "SOCIAL_LISTENING"), row("DOC-1-P2", "PDF_KNOWLEDGE")],
     ["SOCIAL-1", "DOC-1-P2"], "FORMAL_DECISION_MISSING_FORMAL_RECORD"),
    ("BAWASLU telah menetapkan pelanggaran. [INT-999]",
     [row("INT-1", "FORMAL_INTELLIGENCE")], [],
     "FORMAL_DECISION_NO_LOCAL_AUTHORIZED_CITATION"),
])
def test_definitive_claim_without_formal_record_triggers_review(answer,evidence,cited,reason):
    result = evaluate_claim_provenance(evidence,answer,cited)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["review_items"][0]["reason"] == reason
    assert result["formal_decision_verified"] is False


def test_local_formal_reference_does_not_prove_decision():
    result=evaluate_claim_provenance(
        [row("INT-1","FORMAL_INTELLIGENCE")],
        "BAWASLU telah menetapkan pelanggaran. [INT-1]",["INT-1"])
    assert result["status"] == "NOT_APPLICABLE"
    assert result["formal_decision_verified"] is False


def test_hedged_claim_is_not_asserted_as_fact():
    result=evaluate_claim_provenance([],
        "BAWASLU diduga telah menetapkan pelanggaran.",[])
    assert result["status"] == "NOT_APPLICABLE"


def test_reported_speech_not_ascribed_to_assistant():
    result=evaluate_claim_provenance([],
        "Menurut sumber, BAWASLU telah menetapkan pelanggaran.",[])
    assert result["status"] == "NOT_APPLICABLE"


def test_unrelated_formal_reference_in_previous_sentence_not_borrowed():
    result=evaluate_claim_provenance(
        [row("INT-1","FORMAL_INTELLIGENCE")],
        "Riwayat [INT-1]. BAWASLU telah menetapkan pelanggaran.",["INT-1"])
    assert result["review_items"][0]["reason"]=="FORMAL_DECISION_NO_LOCAL_AUTHORIZED_CITATION"


def test_standalone_immediately_following_formal_reference_allowed():
    result=evaluate_claim_provenance(
        [row("INT-1","FORMAL_INTELLIGENCE")],
        "BAWASLU telah menetapkan pelanggaran.\n[INT-1]",["INT-1"])
    assert result["status"] == "NOT_APPLICABLE"
