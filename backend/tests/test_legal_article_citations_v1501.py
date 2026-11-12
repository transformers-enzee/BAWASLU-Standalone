"""v150.1: cited-page article presence checks never certify legal correctness."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def doc(excerpt,reviewed="OFFICER_REVIEWED",identifier="DOC-71-P2"):
    return {"record_id":identifier,"record_type":"PDF_KNOWLEDGE",
            "document_type":"REGULATION","review_status":reviewed,
            "source_excerpt":excerpt,"legal_currentness_verified":False}

def audit(question,evidence,answer):
    text,cited,metadata=audit_assistant_answer(
        question,evidence,answer,
        profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality(
        question,evidence,text,cited,profile="PDF_GUIDANCE",grounding=metadata)
    check=next(x for x in quality["checks"] if x["id"]=="legal_uncertainty")
    return text,cited,metadata,check

def test_named_article_missing_from_cited_pdf_requires_officer_review():
    page=doc("Pasal 8 mengatur pengawasan awal.")
    answer,cited,meta,check=audit("What does the legal rule say?",[page],
        "Pasal 21 authorizes an immediate penalty. [DOC-71-P2]")
    assert cited==["DOC-71-P2"]
    assert meta["legal_article_numbers_mentioned"]==["21"]
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["21"]
    assert meta["legal_article_reference_needs_review"] is True
    assert "Legal article caution" in answer
    assert check["status"]=="REVIEW_REQUIRED"
    assert meta["legal_currentness_verified"] is False
    assert meta["legal_article_semantic_support_verified"] is False

def test_mention_present_on_cited_page_is_not_legal_verification():
    page=doc("Pasal 21 ayat (2): bukti laporan harus diperiksa.")
    answer,cited,meta,check=audit("Explain Pasal 21", [page],
        "Pasal 21 provides procedural context. [DOC-71-P2]")
    assert meta["legal_article_numbers_mentioned"]==["21"]
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==[]
    assert meta["legal_article_semantic_support_verified"] is False
    assert meta["legal_currentness_verified"] is False
    assert meta["legal_verdict_confirmed"] is False
    assert check["status"]=="PASS"

def test_uncited_or_social_card_cannot_validate_article_number():
    legal=doc("Pasal 19 is mentioned here.")
    answer,cited,meta,check=audit("Explain Pasal 19",[legal],
        "Pasal 19 establishes a sanction.")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["19"]
    assert check["status"]=="REVIEW_REQUIRED"
    assert "Legal article caution" in answer
    social={"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Pasal 19"}
    answer,cited,meta,check=audit("What does Pasal 19 mean?",[legal,social],
        "Pasal 19 is confirmed. [SOCIAL-1]")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["19"]
    assert check["status"]=="REVIEW_REQUIRED"

def test_multiple_articles_and_unreviewed_docs_are_conservative():
    a=doc("Pasal 12 and Pasal 15 are cited.",reviewed="UNREVIEWED")
    answer,_,meta,check=audit("Explain articles",[a],
        "Pasal 12, Pasal 15, and Pasal 16 apply. [DOC-71-P2]")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["16"]
    assert check["status"]=="REVIEW_REQUIRED"
    assert meta["cited_unreviewed_pdf_pages"]==1
    assert "Source caution" in answer

def test_unrelated_document_cannot_satisfy_unmatched_citation():
    cited=doc("Pasal 1 allows intake.",identifier="DOC-71-P2")
    unrelated=doc("Pasal 98 sanctions",identifier="DOC-72-P3")
    answer,_,meta,check=audit("Explain Pasal 98",[cited,unrelated],
        "Pasal 98 authorizes an action. [DOC-71-P2]")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["98"]
    assert check["status"]=="REVIEW_REQUIRED"
