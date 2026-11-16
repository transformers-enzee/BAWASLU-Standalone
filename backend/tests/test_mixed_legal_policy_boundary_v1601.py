"""v160.1 mixed-platform/legal attribution remains warning-only, not a ruling."""
import pytest
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def page(ref,body,kind="REGULATION"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"review_status":"OFFICER_REVIEWED",
            "legal_version_label":"review copy",
            "legal_effective_date":"2026-01-01",
            "source_excerpt":body}

def evaluate(answer,rows=None,question="What legal and platform policy applies?"):
    evidence=rows if rows is not None else [page("DOC-1-P1","Election law provides Pasal 21.")]
    visible,cited,audit=audit_assistant_answer(question,evidence,answer,
                                              profile="PDF_GUIDANCE",language="en")
    qa=evaluate_answer_quality(question,evidence,visible,cited,
                               profile="PDF_GUIDANCE",grounding=audit)
    return audit,qa

def test_article_wrong_standalone_next_line_is_caught():
    a,q=evaluate("Pasal 21 applies.\n[DOC-1-P1]",
        [page("DOC-1-P1","Pasal 8 is mentioned in this rule.")])
    assert a["legal_article_claim_citation_mismatch_count"]==1
    assert a["legal_article_claims_without_local_pdf_citation"]==[]
    assert q["legal_review_summary"]["status"]=="OFFICER_REVIEW_REQUIRED"

def test_right_standalone_next_line_article_is_not_false_mismatch():
    a,q=evaluate("Pasal 21 applies.\n[DOC-1-P1]")
    assert a["legal_article_claim_citation_mismatch_count"]==0
    assert not a["legal_article_claims_without_local_pdf_citation"]

def test_other_narrative_sentence_does_not_lend_citation():
    a,_=evaluate("Pasal 21 applies. Further reading [DOC-1-P1].")
    assert a["legal_article_claims_without_local_pdf_citation"]==["21"]

@pytest.mark.parametrize("answer",[
    "Instagram violates platform policy [DOC-1-P1].",
    "TikTok breaches community guidelines [DOC-1-P1].",
    "Facebook is in violation of platform rules [DOC-1-P1].",
    "Instagram melanggar kebijakan platform [DOC-1-P1].",
    "TikTok terbukti melanggar aturan komunitas [DOC-1-P1].",
])
def test_platform_verdict_using_legal_citation_requires_review(answer):
    _,q=evaluate(answer)
    p=q["platform_policy_legal_boundary"]
    assert p["status"]=="REVIEW_REQUIRED"
    assert p["possible_platform_policy_verdicts"]==1
    assert p["review_items"][0]["cited_legal_page_ids"]==["DOC-1-P1"]
    summary=q["legal_review_summary"]
    issue=next(x for x in summary["issues"] if x["code"]=="PLATFORM_POLICY_BOUNDARY")
    assert issue["priority"]=="P2"
    assert issue["source_ids"]==["DOC-1-P1"]
    assert summary["automated_legal_approval"] is False
    assert p["platform_breach_confirmed"] is False

@pytest.mark.parametrize("answer",[
    "Instagram may violate platform policy [DOC-1-P1].",
    "TikTok potentially breaches community guidelines [DOC-1-P1].",
    "Instagram diduga melanggar kebijakan platform [DOC-1-P1].",
    "According to sources, Facebook violates platform policy [DOC-1-P1].",
    "The legal document is not a platform policy [DOC-1-P1].",
])
def test_uncertain_or_quoted_platform_claim_not_treated_as_verdict(answer):
    _,q=evaluate(answer)
    assert q["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_nonlegal_citation_cannot_be_election_law_support():
    _,q=evaluate("Instagram violates platform policy [DOC-2-P1].",
        [page("DOC-2-P1","Some uploaded report about Instagram","REPORT")])
    assert q["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_unselected_citation_is_not_legal_support():
    a,q=evaluate("Instagram violates platform policy [DOC-999-P1].")
    assert a["rejected_unavailable_citations"]==1
    assert q["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0

def test_no_legal_question_does_not_invent_legal_boundary_review():
    _,q=evaluate("Instagram violates platform policy [DOC-1-P1]",
        question="Summarize these records")
    assert q["platform_policy_legal_boundary"]["status"]=="NOT_APPLICABLE"

def test_human_accuracy_remains_unmeasured():
    _,q=evaluate("Instagram violates platform policy [DOC-1-P1].")
    assert q["human_accuracy"] is None
    assert q["claim_truth_verified"] is False
    assert q["legal_currentness_verified"] is False
    assert q["legal_verdict_confirmed"] is False
