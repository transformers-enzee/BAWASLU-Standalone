"""v150.6: categorical legal claims without direct orders or article numbers."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def page():
    return {"record_id":"DOC-51-P1","record_type":"PDF_KNOWLEDGE",
            "review_status":"OFFICER_REVIEWED","document_type":"REGULATION",
            "source_excerpt":"The report outlines a review procedure, not a confirmed verdict.",
            "legal_currentness_verified":False}

def audit(sentence,question="Summarize this case",evidence=None,language="en"):
    evidence=[page()] if evidence is None else evidence
    response,cited,meta=audit_assistant_answer(
        question,evidence,sentence,profile="PDF_GUIDANCE",language=language)
    qa=evaluate_answer_quality(question,evidence,response,cited,
                               profile="PDF_GUIDANCE",grounding=meta)
    legal=next(x for x in qa["checks"] if x["id"]=="legal_uncertainty")
    return response,meta,legal

def test_definitive_guilt_cannot_pass_with_reviewed_pdf():
    response,meta,legal=audit("The candidate is guilty. [DOC-51-P1]")
    assert meta["legal_categorical_outcome_flags"]==["ASSERTED_LEGAL_GUILT"]
    assert meta["legal_categorical_outcome_needs_officer_review"] is True
    assert "Legal certainty caution" in response
    assert legal["status"]=="REVIEW_REQUIRED"
    assert meta["legal_verdict_confirmed"] is False

def test_confirmed_electoral_violation_without_article_triggers_review():
    response,meta,legal=audit(
        "The evidence confirms an electoral violation. [DOC-51-P1]",
        question="Summarize the records")
    assert meta["legal_categorical_outcome_flags"]==["ASSERTED_CONFIRMED_VIOLATION"]
    assert legal["status"]=="REVIEW_REQUIRED"
    assert meta["legal_currentness_verified"] is False

def test_indonesian_guilt_or_sanction_outcome_triggers_review():
    for statement,expected in [
        ("Calon ini terbukti bersalah. [DOC-51-P1]","ASSERTED_LEGAL_GUILT"),
        ("Pelaku telah didiskualifikasi. [DOC-51-P1]","ASSERTED_ENFORCEMENT_OUTCOME"),
        ("Pelanggaran ini telah terbukti. [DOC-51-P1]","ASSERTED_CONFIRMED_VIOLATION"),
    ]:
        response,meta,legal=audit(statement,language="id")
        assert expected in meta["legal_categorical_outcome_flags"]
        assert "Peringatan kepastian hukum" in response
        assert legal["status"]=="REVIEW_REQUIRED"

def test_uncertainty_and_qualified_allegations_are_not_categorical():
    for sentence in [
        "The candidate is allegedly guilty. [DOC-51-P1]",
        "The violation is not confirmed. [DOC-51-P1]",
        "The candidate may be convicted. [DOC-51-P1]",
        "Dugaan pelanggaran ini belum terbukti. [DOC-51-P1]",
        "It is necessary to verify the allegation. [DOC-51-P1]",
    ]:
        _,meta,_=audit(sentence)
        assert meta["legal_categorical_outcome_flags"]==[]

def test_quote_or_question_does_not_create_automatic_legal_verdict():
    for sentence in [
        'According to reports, the candidate is guilty. [DOC-51-P1]',
        '"The candidate is guilty." [DOC-51-P1]',
        "Is the candidate guilty? [DOC-51-P1]",
    ]:
        _,meta,_=audit(sentence)
        assert meta["legal_categorical_outcome_flags"]==[]

def test_new_positive_clause_after_negation_is_detected():
    response,meta,legal=audit(
        "The report is not confirmed, but the candidate is guilty. [DOC-51-P1]")
    assert "ASSERTED_LEGAL_GUILT" in meta["legal_categorical_outcome_flags"]
    assert legal["status"]=="REVIEW_REQUIRED"
    assert "Legal certainty caution" in response

def test_absent_pdf_does_not_certify_definitive_legal_conclusion():
    response,meta,legal=audit("The official has been convicted.",evidence=[])
    assert meta["legal_categorical_outcome_needs_officer_review"] is True
    assert legal["status"]=="REVIEW_REQUIRED"
    assert meta["audit_used_paid_provider"] is False

def test_neutral_casework_summary_does_not_raise_false_guilt_claim():
    text,meta,legal=audit(
        "Evidence is pending officer review. [DOC-51-P1]",
        question="Summarize the procedure")
    assert meta["legal_categorical_outcome_flags"]==[]
    assert "Legal certainty caution" not in text
    assert legal["status"]=="PASS"
