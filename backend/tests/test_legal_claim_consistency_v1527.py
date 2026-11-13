"""v152.7: narrow lexical polarity reversal QA, without semantic validation."""
from app.assistant_claim_consistency import evaluate_legal_claim_consistency as check
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def legal(ref,excerpt,kind="REGULATION"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"review_status":"OFFICER_REVIEWED",
            "source_excerpt":excerpt}

def run(question,rows,answer):
    visible,cited,ground=audit_assistant_answer(
        question,rows,answer,profile="PDF_GUIDANCE",language="en")
    result=evaluate_answer_quality(question,rows,visible,cited,
                                   profile="PDF_GUIDANCE",grounding=ground)
    return result["legal_claim_passage_consistency"],result

def test_reverse_must_not_report_vs_must_report_is_flagged():
    x,_=run("What does legal guidance say?",
            [legal("DOC-1-P1","Officials must not report incidents.")],
            "Officials must report incidents [DOC-1-P1].")
    assert x["status"]=="REVIEW_REQUIRED"
    assert x["possible_reversal_count"]==1
    assert x["possible_reversals"][0]["cited_page_id"]=="DOC-1-P1"

def test_identical_obligation_wording_is_not_certified_correct():
    x,q=run("What does the law say?",
            [legal("DOC-1-P1","Officials must report incidents.")],
            "Officials must report incidents [DOC-1-P1].")
    assert x["possible_reversal_count"]==0
    assert x["status"]=="NOT_APPLICABLE"
    assert x["semantic_entailment_verified"] is False
    assert q["semantic_entailment_verified"] is False

def test_report_with_matching_wording_cannot_hide_legal_reversal():
    x,_=run("What does law require?",
            [legal("DOC-1-P1","Officials must not report incidents."),
             legal("DOC-2-P1","Officials must report incidents.","REPORT")],
            "Officials must report incidents [DOC-1-P1] [DOC-2-P1].")
    assert x["possible_reversal_count"]==1

def test_uncited_legal_page_does_not_trigger_flag():
    x,_=run("What law applies?",
            [legal("DOC-1-P1","Officials must not report incidents."),
             legal("DOC-2-P1","Officials must report incidents.")],
            "Officials must report incidents [DOC-2-P1].")
    assert x["possible_reversal_count"]==0

def test_other_sentence_legal_page_cannot_trigger_or_satisfy_local_consistency():
    x,_=run("What law applies?",
            [legal("DOC-1-P1","Officials must not report incidents.")],
            "Legal source [DOC-1-P1]. Officials must report incidents.")
    assert x["checked_claim_spans"]==0
    assert x["possible_reversal_count"]==0

def test_indonesian_wajib_vs_tidak_wajib_flags():
    x,_=run("Apa kewajiban hukum?",
            [legal("DOC-1-P1","Petugas tidak wajib melapor.")],
            "Petugas wajib melapor [DOC-1-P1].")
    assert x["status"]=="REVIEW_REQUIRED"

def test_different_action_does_not_create_false_positive():
    x,_=run("What law applies?",
            [legal("DOC-1-P1","Officials must not register.")],
            "Officials must report incidents [DOC-1-P1].")
    assert x["possible_reversal_count"]==0

def test_mixed_source_provisions_are_ambiguous_not_contradiction():
    x,_=run("What law applies?",
            [legal("DOC-1-P1","Officials must report. Other officials must not report.")],
            "Officials must report incidents [DOC-1-P1].")
    assert x["possible_reversal_count"]==0

def test_plain_nonlegal_question_is_not_checked():
    x,_=run("Summarize records",[legal("DOC-1-P1","Officials must not report.")],
            "Officials must report [DOC-1-P1].")
    assert x["status"]=="NOT_APPLICABLE"
    assert x["checked_claim_spans"]==0

def test_unauthorized_reference_never_enters_claim_comparison():
    x,_=run("Which law applies?",
            [legal("DOC-1-P1","Officials must not report.")],
            "Officials must report [DOC-99-P1].")
    assert x["possible_reversal_count"]==0

def test_source_with_no_modal_verb_is_unknown_not_pass():
    x,_=run("What does the law require?",
            [legal("DOC-1-P1","Reporting duties are described here.")],
            "Officials must report incidents [DOC-1-P1].")
    assert x["status"]=="NOT_APPLICABLE"
    assert x["semantic_entailment_verified"] is False
