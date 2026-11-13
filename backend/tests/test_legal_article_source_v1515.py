"""v151.5 legal article citations cannot be supported by contextual reports."""
from app.assistant_grounding import audit_assistant_answer

def pdf(ref,kind,excerpt="Pasal 21 is mentioned here."):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE","document_type":kind,
            "review_status":"OFFICER_REVIEWED","source_excerpt":excerpt}

def audit(rows,answer):
    return audit_assistant_answer("What does Pasal 21 say?",rows,answer,
                                  profile="PDF_GUIDANCE",language="en")[2]

def test_report_only_same_sentence_citation_is_not_legal_support():
    meta=audit([pdf("DOC-4-P1","REPORT")], "Pasal 21 applies [DOC-4-P1].")
    assert meta["legal_article_claims_without_local_pdf_citation"]==["21"]
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_NONLEGAL_PDF_ONLY"

def test_report_on_next_line_does_not_supply_legal_attribution():
    meta=audit([pdf("DOC-4-P1","REPORT")], "Pasal 21 applies.\n[DOC-4-P1]")
    assert meta["legal_article_claims_without_local_pdf_citation"]==["21"]

def test_mixed_context_and_regulation_checks_only_legal_page():
    meta=audit([pdf("DOC-4-P1","REPORT"),pdf("DOC-5-P2","REGULATION","Pasal 30 appears.")],
               "Pasal 21 applies [DOC-4-P1] [DOC-5-P2].")
    assert meta["legal_article_claim_citation_mismatch_count"]==1
    assert meta["legal_article_claim_citation_mismatches"][0]["cited_page_ids"]==["DOC-5-P2"]

def test_matching_regulation_still_passes_lexical_attribution():
    meta=audit([pdf("DOC-5-P2","REGULATION")], "Pasal 21 is discussed [DOC-5-P2].")
    assert meta["legal_article_claim_citation_mismatch_count"]==0
    assert meta["legal_article_claims_without_local_pdf_citation"]==[]
