"""v160.4: explicit cross-module provenance and platform-only source boundary."""
import pytest
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def social(ref):
    return {"record_id":ref,"record_type":"SOCIAL_LISTENING",
            "source_excerpt":"A public post alleges possible irregularities."}

def legal(ref):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":"REGULATION","review_status":"OFFICER_REVIEWED",
            "source_excerpt":"Pasal 21 describes BAWASLU reporting procedures.",
            "legal_version_label":"review draft","legal_effective_date":"2026-01-01"}

def intel(ref):
    return {"record_id":ref,"record_type":"FORMAL_INTELLIGENCE",
            "source_excerpt":"A review record is pending officer confirmation."}

def assess(answer,records=None,question="Summarize the collected posts"):
    records=records if records is not None else [social("SOCIAL-1")]
    visible,cited,ground=audit_assistant_answer(
        question,records,answer,profile="CROSS_MODULE_REVIEW",language="en")
    return evaluate_answer_quality(question,records,visible,cited,
                                   profile="CROSS_MODULE_REVIEW",grounding=ground)

@pytest.mark.parametrize("claim",[
    "BAWASLU confirmed an electoral violation",
    "BAWASLU has formally confirmed a violation",
    "BAWASLU established a legal offence",
    "BAWASLU telah menetapkan pelanggaran",
    "BAWASLU secara resmi mengonfirmasi pelanggaran",
])
def test_formal_verdict_social_only_requires_human_review(claim):
    q=assess(claim+" [SOCIAL-1].")
    check=q["formal_outcome_source_provenance"]
    assert check["status"]=="REVIEW_REQUIRED"
    assert check["review_required_count"]==1
    assert check["review_items"][0]["cited_social_ids"]==["SOCIAL-1"]
    issue=next(x for x in q["legal_review_summary"]["issues"]
               if x["code"]=="FORMAL_OUTCOME_SOCIAL_ONLY")
    assert issue["priority"]=="P1"
    assert issue["source_ids"]==["SOCIAL-1"]
    assert check["formal_decision_verified"] is False
    assert q["human_accuracy"] is None

def test_multiple_distinct_claims_preserve_local_source_ids():
    q=assess("BAWASLU confirmed a violation [SOCIAL-1]. "
             "BAWASLU confirmed an electoral violation [SOCIAL-2].",
             [social("SOCIAL-1"),social("SOCIAL-2"),intel("INT-5")])
    check=q["formal_outcome_source_provenance"]
    assert check["review_required_count"]==2
    assert [item["cited_social_ids"] for item in check["review_items"]]==[
        ["SOCIAL-1"],["SOCIAL-2"]]
    assert q["legal_review_summary"]["priority_counts"]["P1"]>=1

def test_standalone_next_line_local_social_citation():
    q=assess("BAWASLU confirmed a violation.\n[SOCIAL-1]")
    assert q["formal_outcome_source_provenance"]["review_required_count"]==1

@pytest.mark.parametrize("claim",[
    "BAWASLU allegedly confirmed a violation [SOCIAL-1].",
    "Reportedly BAWASLU confirmed a violation [SOCIAL-1].",
    "According to sources, BAWASLU confirmed a violation [SOCIAL-1].",
    "BAWASLU may have confirmed a violation [SOCIAL-1].",
    "BAWASLU diduga telah menetapkan pelanggaran [SOCIAL-1].",
])
def test_hedged_or_attributed_claim_not_categorical(claim):
    q=assess(claim)
    assert q["formal_outcome_source_provenance"]["review_required_count"]==0

def test_formal_and_social_refs_not_treated_as_social_only():
    q=assess("BAWASLU confirmed an electoral violation [SOCIAL-1] [INT-5].",
             [social("SOCIAL-1"),intel("INT-5")])
    assert q["formal_outcome_source_provenance"]["review_required_count"]==0
    assert q["formal_outcome_source_provenance"]["formal_decision_verified"] is False

def test_unselected_id_not_used_as_source_certification():
    q=assess("BAWASLU confirmed a violation [SOCIAL-99].")
    assert q["formal_outcome_source_provenance"]["review_required_count"]==0

def test_next_sentence_social_citation_not_borrowed():
    q=assess("BAWASLU confirmed a violation. Other commentary [SOCIAL-1].")
    assert q["formal_outcome_source_provenance"]["review_required_count"]==0

def test_plain_social_discussion_without_formal_decision_stays_unflagged():
    q=assess("A post alleged an electoral violation [SOCIAL-1].")
    assert q["formal_outcome_source_provenance"]["review_required_count"]==0

@pytest.mark.parametrize("claim",[
    "Instagram violates platform policy [DOC-1-P1].",
    "TikTok breaches community guidelines [DOC-1-P1].",
    "Instagram melanggar kebijakan platform [DOC-1-P1].",
])
def test_platform_only_question_still_flags_legal_pdf_misattribution(claim):
    q=assess(claim,[legal("DOC-1-P1")],question="Does this platform post breach guidelines?")
    boundary=q["platform_policy_legal_boundary"]
    assert boundary["possible_platform_policy_verdicts"]==1
    assert boundary["platform_breach_confirmed"] is False
    summary=q["legal_review_summary"]
    assert summary["applicable"] is True
    assert any(x["code"]=="PLATFORM_POLICY_BOUNDARY" for x in summary["issues"])
    assert summary["automated_legal_approval"] is False

def test_platform_only_question_without_legal_source_is_not_a_legal_pdf_warning():
    q=assess("Instagram violates platform policy [SOCIAL-1].")
    assert q["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0
    assert q["platform_policy_legal_boundary"]["platform_breach_confirmed"] is False

def test_platform_uncertainty_still_not_definitive():
    q=assess("Instagram may violate platform policy [DOC-1-P1].",
             [legal("DOC-1-P1")])
    assert q["platform_policy_legal_boundary"]["possible_platform_policy_verdicts"]==0
