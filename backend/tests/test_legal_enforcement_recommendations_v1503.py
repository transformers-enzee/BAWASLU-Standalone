"""v150.3: assertive legal enforcement recommendations do not auto-pass."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def paper(status="OFFICER_REVIEWED"):
    return {"record_id":"DOC-31-P2","record_type":"PDF_KNOWLEDGE",
            "review_status":status,"document_type":"REGULATION",
            "source_excerpt":"Pasal 21: Petugas melakukan pemeriksaan bukti sebelum laporan diteruskan.",
            "legal_currentness_verified":False}

def assessed(answer,question="What legal follow-up is required?",status="OFFICER_REVIEWED"):
    evidence=[paper(status)]
    output,cited,meta=audit_assistant_answer(
        question,evidence,answer,profile="PDF_GUIDANCE",language="en")
    qa=evaluate_answer_quality(question,evidence,output,cited,
                               profile="PDF_GUIDANCE",grounding=meta)
    legal=next(x for x in qa["checks"] if x["id"]=="legal_uncertainty")
    return output,meta,legal

def test_assertive_arrest_directive_fails_closed_with_reviewed_pdf():
    text,meta,legal=assessed("The officer must arrest the suspect. [DOC-31-P2]")
    assert meta["cited_officer_reviewed_legal_pages"]==1
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True
    assert legal["status"]=="REVIEW_REQUIRED"
    assert "Enforcement caution" in text
    assert meta["legal_verdict_confirmed"] is False
    assert meta["legal_currentness_verified"] is False

def test_indonesian_punitive_directive_requires_review():
    evidence=[paper()]
    text,cited,meta=audit_assistant_answer(
        "Apakah ada sanksi hukum?",evidence,
        "Pelaku wajib ditahan. [DOC-31-P2]",
        profile="PDF_GUIDANCE",language="id")
    assert "Peringatan tindakan hukum" in text
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True

def test_pure_procedure_does_not_trigger_enforcement_flag():
    text,meta,legal=assessed("Pasal 21 requires reviewing evidence. [DOC-31-P2]")
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is False
    assert legal["status"]=="PASS"

def test_question_or_negated_directive_is_not_a_positive_enforcement_recommendation():
    for answer in ("Should the officer arrest the person? [DOC-31-P2]",
                   "The officer must not arrest anyone without verification. [DOC-31-P2]",
                   "Petugas tidak wajib ditahan. [DOC-31-P2]"):
        _,meta,_=assessed(answer)
        assert meta["legal_enforcement_recommendation_needs_officer_review"] is False

def test_no_document_cannot_certify_assertive_enforcement():
    answer,cited,meta=audit_assistant_answer(
        "What should happen?",[],
        "Officials must prosecute immediately.",
        profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality("What should happen?",[],answer,cited,
                                    profile="PDF_GUIDANCE",grounding=meta)
    legal=next(x for x in quality["checks"] if x["id"]=="legal_uncertainty")
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True
    assert legal["status"]=="REVIEW_REQUIRED"
    assert meta["audit_used_paid_provider"] is False
