"""v152.8: warning-only legal date and quantity grounding tests."""
from app.assistant_answer_quality import evaluate_answer_quality
from app.assistant_grounding import audit_assistant_answer
from app.assistant_numeric_claims import _facts

def pdf(ref,body,kind="REGULATION"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"review_status":"OFFICER_REVIEWED",
            "source_excerpt":body}

def assess(answer,records,question="Which law governs the deadline?"):
    answer,cited,ground=audit_assistant_answer(
        question,records,answer,profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality(question,records,answer,cited,
                                    profile="PDF_GUIDANCE",grounding=ground)
    return quality["legal_numeric_claim_source_alignment"],quality

def test_duration_not_present_in_cited_legal_page_requires_review():
    signal,_=assess("The deadline is 30 days [DOC-1-P1].",
                    [pdf("DOC-1-P1","Submission deadline: 14 days.")])
    assert signal["status"]=="REVIEW_REQUIRED"
    assert signal["unsupported_details"][0]["kind"]=="QUANTITY"
    assert signal["unsupported_details"][0]["detail"]=="30 day"

def test_exact_cited_duration_remains_unverified_not_pass():
    signal,q=assess("The deadline is 14 days [DOC-1-P1].",
                    [pdf("DOC-1-P1","Submission deadline: 14 days.")])
    assert signal["unsupported_detail_count"]==0
    assert signal["status"]=="NOT_APPLICABLE"
    assert q["semantic_entailment_verified"] is False

def test_unrelated_report_cannot_supply_numeric_support():
    signal,_=assess("Deadline 30 days [DOC-1-P1] [DOC-2-P1].",
                    [pdf("DOC-1-P1","Deadline 14 days."),
                     pdf("DOC-2-P1","Deadline 30 days.","REPORT")])
    assert signal["unsupported_detail_count"]==1
    assert signal["unsupported_details"][0]["cited_page_ids"]==["DOC-1-P1"]

def test_uncited_regulation_cannot_supply_numeric_support():
    signal,_=assess("Deadline 30 days [DOC-1-P1].",
                    [pdf("DOC-1-P1","Deadline 14 days."),
                     pdf("DOC-2-P1","Deadline 30 days.")])
    assert signal["unsupported_detail_count"]==1

def test_same_sentence_multiple_legal_pages_can_supply_exact_detail():
    signal,_=assess("Deadline 30 days [DOC-1-P1] [DOC-2-P1].",
                    [pdf("DOC-1-P1","Deadline 14 days."),
                     pdf("DOC-2-P1","Deadline 30 days.")])
    assert signal["unsupported_detail_count"]==0

def test_date_not_present_in_page_requires_officer_review():
    signal,_=assess("The rule is effective 2026-11-01 [DOC-1-P1].",
                    [pdf("DOC-1-P1","The rule is effective 2026-10-01.")])
    assert signal["unsupported_details"][0]["kind"]=="DATE"

def test_identical_date_is_not_legal_currentness_verification():
    signal,_=assess("The rule is effective 2026-11-01 [DOC-1-P1].",
                    [pdf("DOC-1-P1","The rule is effective 2026-11-01.")])
    assert signal["unsupported_detail_count"]==0
    assert signal["legal_currentness_verified"] is False

def test_pasal_number_without_quantity_unit_is_not_double_counted():
    signal,_=assess("Pasal 21 applies [DOC-1-P1].",
                    [pdf("DOC-1-P1","Pasal 21 contains election regulations.")])
    assert signal["checked_claim_spans"]==0

def test_percent_sign_is_detected_without_confusing_page_id():
    signal,_=assess("The threshold is 25% [DOC-1-P1].",
                    [pdf("DOC-1-P1","The threshold is 10 percent.")])
    assert signal["unsupported_detail_count"]==1

def test_report_only_citation_is_not_evaluated_as_legal_support():
    signal,_=assess("Deadline 30 days [DOC-2-P1].",
                    [pdf("DOC-2-P1","Deadline 30 days.","REPORT")])
    assert signal["checked_claim_spans"]==0

def test_next_line_authorized_pdf_citation_can_support_quantity():
    signal,_=assess("Deadline 30 days.\n[DOC-1-P1]",
                    [pdf("DOC-1-P1","Deadline 30 days.")])
    assert signal["unsupported_detail_count"]==0

def test_nonlegal_question_does_not_produce_warning():
    signal,_=assess("Campaign metrics 30 days [DOC-1-P1].",
                    [pdf("DOC-1-P1","Report 14 days.")],
                    "Summarize these uploaded records")
    assert signal["status"]=="NOT_APPLICABLE"

def test_indonesian_duration_without_exact_text_is_flagged():
    signal,_=assess("Batas waktu 30 hari [DOC-1-P1].",
                    [pdf("DOC-1-P1","Batas waktu 14 hari.")],
                    "Apa batas waktu menurut hukum?")
    assert signal["unsupported_detail_count"]==1

def test_unsupported_reference_cannot_satisfy_numeric_claim():
    signal,_=assess("Deadline 30 days [DOC-99-P1].",
                    [pdf("DOC-1-P1","Deadline 30 days.")])
    assert signal["checked_claim_spans"]==0

def test_date_with_no_normative_intent_is_not_flagged():
    signal,_=assess("This PDF was scanned on 2026-11-01 [DOC-1-P1].",
                    [pdf("DOC-1-P1","Contains election reporting procedures.")])
    assert signal["unsupported_detail_count"]==0

def test_thousands_or_ordinary_count_without_units_is_not_flagged():
    signal,_=assess("The report recorded 120 events [DOC-1-P1].",
                    [pdf("DOC-1-P1","The report recorded 50 events.")])
    assert signal["unsupported_detail_count"]==0

def test_decimal_value_and_unit_matching_is_stable():
    dates,quantities=_facts("Batas 12,5 persen dan 30 hari.")
    assert ("12.5","percent") in quantities
    assert ("30","day") in quantities
