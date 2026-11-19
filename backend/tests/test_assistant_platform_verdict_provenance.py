"""No-provider regression cases for unsupported platform-moderation verdicts."""
import pytest
from app.assistant_policy_boundary import evaluate_policy_boundary


def record(identifier, kind, document_type=None):
    return {"record_id": identifier, "record_type": kind,
            "document_type": document_type}


@pytest.mark.parametrize("answer,rows,ids,reason", [
    ("Unggahan TikTok melanggar kebijakan platform.", [], [],
     "PLATFORM_VERDICT_NO_LOCAL_AUTHORIZED_CITATION"),
    ("Unggahan TikTok melanggar kebijakan platform. [SOCIAL-1]",
     [record("SOCIAL-1","SOCIAL_LISTENING")], ["SOCIAL-1"],
     "PLATFORM_VERDICT_WITHOUT_VERIFIED_PROVIDER_DECISION"),
    ("Unggahan TikTok melanggar kebijakan platform. [DOC-1-P4]",
     [record("DOC-1-P4","PDF_KNOWLEDGE","REGULATION")], ["DOC-1-P4"],
     "PLATFORM_VERDICT_CITED_TO_ELECTORAL_LEGAL_REFERENCE"),
    ("TikTok violates community guidelines. [INT-1]",
     [record("INT-1","FORMAL_INTELLIGENCE")], ["INT-1"],
     "PLATFORM_VERDICT_WITHOUT_VERIFIED_PROVIDER_DECISION"),
])
def test_categorical_policy_verdict_requires_review(answer,rows,ids,reason):
    result=evaluate_policy_boundary("",rows,answer,ids)
    assert result["status"]=="REVIEW_REQUIRED"
    assert result["review_items"][0]["reason"]==reason
    assert result["current_platform_policy_verified"] is False


@pytest.mark.parametrize("answer",[
    "Unggahan TikTok berpotensi melanggar kebijakan platform.",
    "Menurut sumber, unggahan TikTok melanggar kebijakan platform.",
    "Apakah unggahan TikTok melanggar kebijakan platform?",
    "Tidak tersedia cukup bukti untuk menilai unggahan TikTok.",
])
def test_hedged_reported_questions_are_not_categorical_verdicts(answer):
    result=evaluate_policy_boundary("",[],answer,[])
    assert result["status"]=="NOT_APPLICABLE"


def test_platform_question_does_not_need_legal_document_to_run_check():
    result=evaluate_policy_boundary("Apakah aturan Instagram berlaku?",[],
        "Unggahan Instagram melanggar kebijakan platform.",[])
    assert result["status"]=="REVIEW_REQUIRED"
