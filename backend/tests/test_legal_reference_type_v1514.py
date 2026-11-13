"""v151.4: distinguish legal reference sources from unrelated PDF context."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def page(id,doc_type="REPORT",review="OFFICER_REVIEWED",excerpt="Pasal 21 appears in this PDF."):
    return {"record_id":id,"record_type":"PDF_KNOWLEDGE",
            "document_type":doc_type,"review_status":review,
            "source_excerpt":excerpt,"legal_currentness_verified":False}
def run(question,items,answer):
    output,cited,meta=audit_assistant_answer(
        question,items,answer,profile="PDF_GUIDANCE",language="en")
    result=evaluate_answer_quality(
        question,items,output,cited,profile="PDF_GUIDANCE",grounding=meta)
    return output,cited,meta,result
def codes(meta):
    return [x["code"] for x in meta["officer_review_steps"]]

def test_report_only_pdf_does_not_claim_legal_reference_is_present():
    _,cited,meta,quality=run("Which law applies?",[page("DOC-7-P1")],
                           "The internal report mentions an allegation [DOC-7-P1].")
    assert cited==["DOC-7-P1"]
    assert meta["cited_pdf_pages"]==1
    assert meta["cited_legal_reference_pages"]==0
    assert meta["cited_nonlegal_pdf_pages"]==1
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_NONLEGAL_PDF_ONLY"
    assert codes(meta)==["LOCATE_AUTHORIZED_LEGAL_REFERENCE"]
    assert meta["human_review_required"] is True
    assert meta["legal_action_ready"] is False
    assert quality["human_accuracy"] is None

def test_report_article_number_does_not_substitute_for_legal_passage():
    response,cited,meta,_=run("Explain Pasal 21",[
        page("DOC-7-P1",excerpt="Pasal 21 is mentioned in this unrelated report.")],
        "Pasal 21 authorizes an action [DOC-7-P1].")
    assert meta["legal_article_numbers_not_found_in_cited_pdf"]==["21"]
    assert meta["cited_legal_reference_pages"]==0
    assert "LOCATE_AUTHORIZED_LEGAL_REFERENCE" in codes(meta)
    assert meta["legal_article_reference_needs_review"] is True

def test_eligible_guidance_pdf_is_retrievable_but_never_currentness_verified():
    _,cited,meta,_=run("Explain the relevant law",[
        page("DOC-3-P1",doc_type="GUIDANCE")],
        "Pasal 21 appears in the guidance [DOC-3-P1].")
    assert meta["cited_legal_reference_pages"]==1
    assert meta["cited_nonlegal_pdf_pages"]==0
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_CITED_UNVERIFIED"
    assert "LOCATE_AUTHORIZED_LEGAL_REFERENCE" not in codes(meta)
    assert meta["legal_currentness_verified"] is False
    assert meta["legal_document_type_eligibility_verified"] is False

def test_mixed_context_and_legal_pdf_review_steps_target_legal_page():
    _,cited,meta,_=run("What is the applicable law?",[
        page("DOC-7-P1",doc_type="REPORT"),
        page("DOC-3-P2",doc_type="REGULATION",review="UNREVIEWED")],
        "A report gives background [DOC-7-P1]. Pasal 21 applies [DOC-3-P2].")
    assert meta["cited_legal_reference_pages"]==1
    assert meta["cited_nonlegal_pdf_pages"]==1
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_CITED_UNVERIFIED"
    assert codes(meta)==["REQUEST_DOCUMENT_REVIEW"]
    assert meta["officer_review_steps"][0]["source_ids"]==["DOC-3-P2"]
    assert meta["cited_unreviewed_pdf_pages"]==1

def test_enforcement_with_nonlegal_pdf_still_requests_legal_source():
    _,_,meta,_=run("Review the incident",[page("DOC-8-P1",doc_type="REPORT")],
                   "The officer must prosecute immediately [DOC-8-P1].")
    assert codes(meta)==[
        "LOCATE_AUTHORIZED_LEGAL_REFERENCE",
        "CONFIRM_AUTHORITY_BEFORE_ANY_ACTION"]
    assert meta["officer_review_steps"][-1]["source_ids"]==[]
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True

def test_unrelated_nonlegal_pdf_does_not_overwrite_valid_regulation_coverage():
    _,_,meta,_=run("Review the legal question",[
        page("DOC-8-P1",doc_type="REPORT"),
        page("DOC-9-P1",doc_type="SOP")],
        "Evidence context [DOC-8-P1]. Pasal 21 is described [DOC-9-P1].")
    assert meta["cited_legal_reference_pages"]==1
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_CITED_UNVERIFIED"
    assert meta["legal_verdict_confirmed"] is False
