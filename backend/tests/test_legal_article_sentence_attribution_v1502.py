"""v150.2: sentence-level PDF article citation mismatches require review."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def page(id,excerpt):
    return {"record_id":id,"record_type":"PDF_KNOWLEDGE",
            "review_status":"OFFICER_REVIEWED","document_type":"REGULATION",
            "source_excerpt":excerpt,"legal_currentness_verified":False}

def check(evidence,answer,question="What legal articles apply?"):
    updated,cited,metadata=audit_assistant_answer(
        question,evidence,answer,profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality(question,evidence,updated,cited,
                                    profile="PDF_GUIDANCE",grounding=metadata)
    legal=next(x for x in quality["checks"] if x["id"]=="legal_uncertainty")
    return updated,metadata,legal

def test_article_present_elsewhere_cannot_rescue_wrong_local_pdf_citation():
    a=page("DOC-10-P1","Pasal 21 defines a reporting step.")
    b=page("DOC-11-P2","Pasal 8 concerns record keeping.")
    text,meta,quality=check([a,b],
        "Pasal 21 authorizes action [DOC-11-P2]. Pasal 8 concerns records [DOC-10-P1].")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==[]
    assert meta["legal_article_claim_citation_mismatch_count"]==2
    assert quality["status"]=="REVIEW_REQUIRED"
    assert "Legal article caution" in text
    assert meta["legal_article_semantic_support_verified"] is False

def test_correct_each_sentence_page_assignment_avoids_false_mismatch():
    a=page("DOC-10-P1","Pasal 21 describes a review step.")
    b=page("DOC-11-P2","Pasal 8 describes evidence.")
    text,meta,quality=check([a,b],
        "Pasal 21 is mentioned [DOC-10-P1]. Pasal 8 is also mentioned [DOC-11-P2].")
    assert meta["legal_article_claim_citation_mismatches"]==[]
    assert meta["legal_article_reference_needs_review"] is False
    assert quality["status"]=="PASS"
    assert meta["legal_currentness_verified"] is False

def test_uncited_context_page_and_social_reference_are_not_local_pdf_authority():
    a=page("DOC-10-P1","Pasal 21")
    b=page("DOC-11-P2","Pasal 8")
    social={"record_id":"SOCIAL-5","record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Pasal 21"}
    text,meta,quality=check([a,b,social],
        "Pasal 21 applies [DOC-11-P2] [SOCIAL-5]. Other pages exist [DOC-10-P1].")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==[]
    assert meta["legal_article_claim_citation_mismatch_count"]==1
    assert quality["status"]=="REVIEW_REQUIRED"

def test_uncited_article_maintains_global_conservative_check():
    a=page("DOC-10-P1","Pasal 8 only.")
    text,meta,quality=check([a],"Pasal 21 applies. See [DOC-10-P1].")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["21"]
    assert quality["status"]=="REVIEW_REQUIRED"

def test_unselected_pdf_citation_cannot_rescue_local_article_match():
    a=page("DOC-10-P1","Pasal 8")
    text,meta,quality=check([a],
        "Pasal 21 applies [DOC-999-P1] and needs review [DOC-10-P1].")
    assert "[DOC-999-P1]" not in text
    assert meta["legal_article_reference_needs_review"] is True
    assert meta["rejected_unavailable_citations"]==1
    assert quality["status"]=="REVIEW_REQUIRED"
