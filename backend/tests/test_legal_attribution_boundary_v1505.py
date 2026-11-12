"""v150.5: preserve separately printed legal citations and reported speech."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def page(id,excerpt):
    return {"record_id":id,"record_type":"PDF_KNOWLEDGE",
            "review_status":"OFFICER_REVIEWED","document_type":"REGULATION",
            "source_excerpt":excerpt,"legal_currentness_verified":False}

def review(answer,docs,question="Explain Pasal 21"):
    output,cited,meta=audit_assistant_answer(
        question,docs,answer,profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality(question,docs,output,cited,
        profile="PDF_GUIDANCE",grounding=meta)
    return output,meta,next(x for x in quality["checks"] if x["id"]=="legal_uncertainty")

def test_standalone_citation_immediately_after_claim_is_accepted():
    records=[page("DOC-1-P1","Pasal 21 is about evidence review.")]
    for answer in [
        "Pasal 21 describes evidence review. [DOC-1-P1]",
        "Pasal 21 describes evidence review.\\n[DOC-1-P1]",
    ]:
        _,meta,legal=review(answer,records)
        assert meta["legal_article_claims_without_local_pdf_citation"]==[]
        assert legal["status"]=="PASS"

def test_story_between_article_claim_and_citation_not_local_support():
    records=[page("DOC-1-P1","Pasal 21 is about evidence review.")]
    _,meta,legal=review(
        "Pasal 21 requires a decision. Another claim follows [DOC-1-P1].",records)
    assert meta["legal_article_claims_without_local_pdf_citation"]==["21"]
    assert legal["status"]=="REVIEW_REQUIRED"

def test_unselected_citation_or_social_ref_cannot_replace_pdf():
    records=[page("DOC-1-P1","Pasal 21 is about evidence review."),
            {"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING"}]
    _,meta,legal=review("Pasal 21 applies. [DOC-999-P9] [SOCIAL-1]",records)
    assert meta["legal_article_claims_without_local_pdf_citation"]==["21"]
    assert meta["rejected_unavailable_citations"]==1
    assert legal["status"]=="REVIEW_REQUIRED"

def test_reported_attribution_with_comma_is_not_instruction():
    records=[page("DOC-1-P1","Pasal 21 is about evidence review.")]
    for quote in [
        "According to reports, the official must arrest the suspect. [DOC-1-P1]",
        "Reportedly, the officer should prosecute the person. [DOC-1-P1]",
        "Menurut sumber, petugas wajib ditahan. [DOC-1-P1]",
    ]:
        _,meta,_=review(quote,records)
        assert meta["legal_enforcement_recommendation_needs_officer_review"] is False

def test_new_directive_after_quoted_or_negated_clause_remains_flagged():
    records=[page("DOC-1-P1","Pasal 21 concerns evidence.")]
    _,meta,legal=review(
        "According to reports, someone should arrest the person, but the officer must prosecute now. [DOC-1-P1]",
        records)
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True
    assert legal["status"]=="REVIEW_REQUIRED"
