"""v160.3: avoid platform-policy rulings falsely grounded in electoral PDFs."""
import pytest
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def source(ref,kind="REGULATION"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"review_status":"OFFICER_REVIEWED",
            "source_excerpt":"This is electoral procedure, not a platform policy.",
            "legal_version_label":"review copy",
            "legal_effective_date":"2026-01-01"}

def assess(answer,rows=None,question="What legal and platform policy applies?"):
    records=rows if rows is not None else [source("DOC-1-P1")]
    visible,cited,g=audit_assistant_answer(
        question,records,answer,profile="PDF_GUIDANCE",language="en")
    return evaluate_answer_quality(question,records,visible,cited,
                                   profile="PDF_GUIDANCE",grounding=g)

@pytest.mark.parametrize("claim",[
    "Instagram violates platform policy.",
    "TikTok breaches community guidelines.",
    "Facebook is in violation of platform rules.",
    "Instagram melanggar kebijakan platform.",
    "TikTok terbukti melanggar aturan komunitas.",
])
def test_standalone_next_line_pdf_citation_flags_provider_verdict(claim):
    qa=assess(claim+"\n[DOC-1-P1]")
    boundary=qa["platform_policy_legal_boundary"]
    assert boundary["possible_platform_policy_verdicts"]==1
    assert boundary["review_items"][0]["cited_legal_page_ids"]==["DOC-1-P1"]
    issues=[x for x in qa["legal_review_summary"]["issues"]
            if x["code"]=="PLATFORM_POLICY_BOUNDARY"]
    assert len(issues)==1 and issues[0]["priority"]=="P2"
    assert issues[0]["source_ids"]==["DOC-1-P1"]
    assert boundary["platform_breach_confirmed"] is False
    assert qa["legal_currentness_verified"] is False

def test_inline_policy_citation_still_flags():
    qa=assess("Instagram violates platform policy [DOC-1-P1].")
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==1

def test_next_narrative_sentence_cannot_supply_local_policy_citation():
    qa=assess("Instagram violates platform policy. See page [DOC-1-P1] for election law.")
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_one_sentence_citation_cannot_support_later_platform_claim():
    qa=assess("Election law is discussed [DOC-1-P1]. Instagram violates platform policy.")
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

@pytest.mark.parametrize("text",[
    "Instagram may violate platform policy.\n[DOC-1-P1]",
    "Instagram potentially violates platform policy.\n[DOC-1-P1]",
    "According to sources, Instagram violates platform policy.\n[DOC-1-P1]",
    "Instagram diduga melanggar kebijakan platform.\n[DOC-1-P1]",
])
def test_uncertainty_and_attributed_reporting_not_definitive(text):
    qa=assess(text)
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_contextual_report_not_policy_authority():
    qa=assess("TikTok breaches community guidelines.\n[DOC-2-P1]",
              [source("DOC-2-P1","REPORT")])
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_unselected_reference_cannot_trigger_review_or_count_as_support():
    qa=assess("Instagram violates platform policy.\n[DOC-999-P1]")
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_platform_only_question_cannot_bypass_source_type_review():
    qa=assess("Instagram violates platform policy.\n[DOC-1-P1]",
              question="Summarize these uploaded posts.")
    assert qa["platform_policy_legal_boundary"]["status"]=="REVIEW_REQUIRED"
    assert qa["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==1
    assert qa["platform_policy_legal_boundary"]["platform_breach_confirmed"] is False

def test_multiple_sources_only_eligible_displayed_legal_pages():
    qa=assess("Instagram violates platform policy.\n[DOC-1-P1] [DOC-2-P1]",
              [source("DOC-1-P1"),source("DOC-2-P1","REPORT")])
    assert qa["platform_policy_legal_boundary"]["review_items"][0]["cited_legal_page_ids"]==["DOC-1-P1"]
