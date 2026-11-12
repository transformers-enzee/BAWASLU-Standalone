"""v150.4 bulk: clause-sensitive enforcement, source-local legal claims, mixed PDF review."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def pdf(identifier,excerpt,status="OFFICER_REVIEWED"):
    return {"record_id":identifier,"record_type":"PDF_KNOWLEDGE",
            "review_status":status,"document_type":"REGULATION",
            "source_excerpt":excerpt,"legal_currentness_verified":False}

def check(answer,records,question="What is the relevant legal rule?"):
    response,cited,metadata=audit_assistant_answer(
        question,records,answer,profile="PDF_GUIDANCE",language="en")
    evaluated=evaluate_answer_quality(question,records,response,cited,
                                      profile="PDF_GUIDANCE",grounding=metadata)
    legal=next(x for x in evaluated["checks"] if x["id"]=="legal_uncertainty")
    return response,metadata,legal

def test_separate_negative_clause_does_not_hide_positive_enforcement():
    p=pdf("DOC-1-P1","Pasal 4 describes evidence review.")
    text,meta,legal=check(
      "Do not arrest without evidence, but the officer must prosecute immediately. [DOC-1-P1]",[p])
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True
    assert "Enforcement caution" in text and legal["status"]=="REVIEW_REQUIRED"

def test_indonesian_separate_clause_and_urgent_enforcement():
    p=pdf("DOC-1-P1","Pasal 4 describes a review.")
    text,meta,legal=check(
      "Jangan langsung menahan, namun pelaku wajib segera ditahan. [DOC-1-P1]",[p])
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True
    assert legal["status"]=="REVIEW_REQUIRED"

def test_negative_or_reported_directive_without_separate_instruction_stays_unflagged():
    p=pdf("DOC-1-P1","Pasal 4 describes evidence.")
    for answer in [
        "The officer must not arrest without verification. [DOC-1-P1]",
        "According to reports, the official must arrest the person. [DOC-1-P1]",
        "Do not arrest without evidence. [DOC-1-P1]",
    ]:
        _,meta,_=check(answer,[p])
        assert meta["legal_enforcement_recommendation_needs_officer_review"] is False

def test_article_claim_not_locally_cited_requires_review_even_if_present_elsewhere():
    p=pdf("DOC-1-P1","Pasal 21 mengatur verifikasi.")
    text,meta,legal=check(
        "Pasal 21 requires verification. Source record is [DOC-1-P1].",[p])
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==[]
    assert meta["legal_article_claims_without_local_pdf_citation"]==["21"]
    assert meta["legal_article_reference_needs_review"] is True
    assert "Legal source caution" in text
    assert legal["status"]=="REVIEW_REQUIRED"

def test_citation_in_same_sentence_does_not_raise_unattributed_warning():
    p=pdf("DOC-1-P1","Pasal 21 mengatur verifikasi.")
    _,meta,legal=check("Pasal 21 is cited [DOC-1-P1].",[p])
    assert meta["legal_article_claims_without_local_pdf_citation_count"]==0
    assert legal["status"]=="PASS"

def test_unreviewed_page_cannot_hide_behind_other_reviewed_legal_page():
    a=pdf("DOC-1-P1","Pasal 3 mengatur pengawasan.")
    b=pdf("DOC-2-P2","Pasal 4 menjelaskan panduan.",status="UNREVIEWED")
    text,meta,legal=check(
        "Pasal 3 is described [DOC-1-P1]. Pasal 4 is described [DOC-2-P2].",[a,b])
    assert meta["cited_officer_reviewed_legal_pages"]==1
    assert meta["cited_unreviewed_pdf_pages"]==1
    assert meta["mixed_review_status_cited_pdf_pages"] is True
    assert legal["status"]=="REVIEW_REQUIRED"
    assert "Source caution" in text

def test_social_citation_cannot_substitute_for_local_pdf_page():
    p=pdf("DOC-1-P1","Pasal 7 mengatur dokumen.")
    social={"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Pasal 7"}
    _,meta,legal=check("Pasal 7 applies [SOCIAL-1]. Other source [DOC-1-P1].",[p,social])
    assert meta["legal_article_claims_without_local_pdf_citation"]==["7"]
    assert legal["status"]=="REVIEW_REQUIRED"
