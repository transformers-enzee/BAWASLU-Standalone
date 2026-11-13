"""v152.5 normative legal claims need their own eligible cited page."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def row(ref,kind="REGULATION"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"review_status":"OFFICER_REVIEWED",
            "source_excerpt":"Pemilu election reporting obligations."}

def audit(answer,rows=None,question="Which electoral law applies?"):
    evidence=rows or [row("DOC-1-P1")]
    visible,cited,meta=audit_assistant_answer(question,evidence,answer,
                                              profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality(question,evidence,visible,cited,
                                    profile="PDF_GUIDANCE",grounding=meta)
    return visible,meta,quality

def test_other_sentence_citation_cannot_cover_following_claim():
    _,meta,quality=audit("Reference [DOC-1-P1]. Officials must report incidents.")
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==1
    assert "LEGAL_CLAIM_LOCAL_CITATION" in meta["legal_review_reason_codes"]
    assert quality["checks"][2]["status"]=="REVIEW_REQUIRED"

def test_local_legal_page_attribution_does_not_claim_semantic_support():
    _,meta,_=audit("Officials must report incidents [DOC-1-P1].")
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==0
    assert meta["legal_claim_semantic_support_verified"] is False

def test_report_only_citation_does_not_support_normative_legal_claim():
    _,meta,_=audit("Candidates wajib melapor [DOC-2-P1].",[row("DOC-2-P1","REPORT")])
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==1
    assert meta["prescriptive_legal_claims_without_local_legal_citation"][0]["cited_reference_ids"]==["DOC-2-P1"]

def test_next_line_standalone_legal_reference_is_accepted():
    _,meta,_=audit("Officials must report incidents.\n[DOC-1-P1]")
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==0

def test_unauthorized_reference_is_removed_before_local_claim_check():
    _,meta,_=audit("Officials must report incidents [DOC-99-P1].")
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==1
    assert meta["rejected_unavailable_citations"]==1

def test_questions_are_not_normative_claims():
    _,meta,_=audit("Must officials report incidents? [DOC-1-P1]")
    assert meta["prescriptive_legal_claims_checked"]==0

def test_reading_context_report_does_not_trigger_on_nonlegal_question():
    _,meta,_=audit("Users must review records [DOC-1-P1].",
                   question="Summarize my documents")
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==0

def test_bilingual_legal_prohibition_requires_local_legal_page():
    _,meta,_=audit("Pelanggaran tersebut dilarang dalam aturan ini.",
                   question="Apa dasar hukum pelanggaran?")
    assert meta["prescriptive_legal_claims_without_local_legal_citation_count"]==1

def test_report_only_claim_reuses_existing_missing_legal_source_step():
    _,meta,_=audit("Officials must report incidents [DOC-2-P1].",
                   [row("DOC-2-P1","REPORT")])
    assert "LEGAL_CLAIM_LOCAL_CITATION" in meta["legal_review_reason_codes"]
    assert [step["code"] for step in meta["officer_review_steps"]]==[
        "LOCATE_AUTHORIZED_LEGAL_REFERENCE"]
