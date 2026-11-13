"""v152.9 consolidated legal review, priority, dedupe and permission QA."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def pdf(ref,kind="REGULATION",body="Official report rule, Pasal 21.",review="OFFICER_REVIEWED",scope="BOTH"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"title":"Election guidance",
            "source_excerpt":body,"review_status":review,
            "legal_election_type":scope,"legal_version_label":"",
            "legal_effective_date":""}

def run(question,rows,answer):
    visible,cited,ground=audit_assistant_answer(
        question,rows,answer,profile="PDF_GUIDANCE",language="en")
    quality=evaluate_answer_quality(question,rows,visible,cited,
                                    profile="PDF_GUIDANCE",grounding=ground)
    return quality["legal_review_summary"],quality,ground

def codes(summary):
    return [x["code"] for x in summary["issues"]]

def test_no_legal_page_yields_one_source_warning_not_relevance_duplicate():
    summary,_,_=run("What legal law applies?",[pdf("DOC-2-P1","REPORT")],
                    "General report [DOC-2-P1].")
    assert codes(summary)==["ELIGIBLE_LEGAL_SOURCE_MISSING"]
    assert summary["human_review_required"] is True
    assert summary["automated_legal_approval"] is False

def test_review_only_references_cited_authorized_ids():
    rows=[pdf("DOC-1-P1",review="UNREVIEWED"),pdf("DOC-2-P1",review="UNREVIEWED")]
    summary,_,_=run("What law applies?",rows,"Pasal 21 [DOC-1-P1].")
    assert "DOCUMENT_REVIEW_PENDING" in codes(summary)
    for issue in summary["issues"]:
        assert "DOC-2-P1" not in issue["source_ids"]
        assert set(issue["source_ids"]).issubset({"DOC-1-P1"})

def test_missing_version_and_effective_date_are_one_issue():
    summary,_,_=run("What legal rules apply?",[pdf("DOC-1-P1")],
                    "Pasal 21 [DOC-1-P1].")
    assert codes(summary).count("VERSION_OR_EFFECTIVE_DATE")==1

def test_present_metadata_does_not_mean_legal_approval():
    doc=pdf("DOC-1-P1")
    doc.update(legal_version_label="2026 edition",legal_effective_date="2026-01-01")
    summary,_,_=run("What legal rules apply?",[doc],"Pasal 21 [DOC-1-P1].")
    assert "VERSION_OR_EFFECTIVE_DATE" not in codes(summary)
    assert summary["legal_currentness_verified"] is False

def test_article_and_prescriptive_gaps_consolidate_into_single_issue():
    summary,_,_=run("What legal rules apply?",
        [pdf("DOC-1-P1",body="Pasal 21.")],
        "Pasal 30 must report. Background [DOC-1-P1].")
    assert codes(summary).count("ARTICLE_OR_CLAIM_ATTRIBUTION")==1
    issue=next(x for x in summary["issues"] if x["code"]=="ARTICLE_OR_CLAIM_ATTRIBUTION")
    assert issue["signal_count"]>=2

def test_numeric_and_date_gaps_are_grouped():
    summary,_,_=run("What legal rule applies?",
        [pdf("DOC-1-P1",body="Deadline is 14 days, effective 2026-10-01.")],
        "Deadline is 30 days [DOC-1-P1]. The rule is effective 2026-11-01 [DOC-1-P1].")
    assert codes(summary).count("NUMERIC_OR_DATE")==1
    issue=next(x for x in summary["issues"] if x["code"]=="NUMERIC_OR_DATE")
    assert issue["signal_count"]==2
    assert set(issue["detail_kinds"])=={"QUANTITY","DATE"}

def test_possible_polarity_reversal_remains_high_priority():
    summary,_,_=run("What legal rules apply?",
        [pdf("DOC-1-P1",body="Officials must not report.")],
        "Officials must report [DOC-1-P1].")
    issue=next(x for x in summary["issues"] if x["code"]=="PASSAGE_POLARITY")
    assert issue["priority"]=="P1"
    assert issue["source_ids"]==["DOC-1-P1"]

def test_mixed_scope_and_relevance_do_not_duplicate_two_review_items():
    summary,_,_=run("Which Pemilu law governs the Riau incident?",
        [pdf("DOC-1-P1",body="Unrelated national record",scope="PILKADA")],
        "General guidance [DOC-1-P1].")
    assert "ELECTION_SCOPE" in codes(summary)
    assert "SOURCE_RELEVANCE" not in codes(summary)

def test_relevance_without_scope_issue_is_reported():
    summary,_,_=run("What legal law governs Riau bribery?",
        [pdf("DOC-1-P1",body="National registration process.")],
        "General guidance [DOC-1-P1].")
    assert "SOURCE_RELEVANCE" in codes(summary)

def test_enforcement_and_categorical_outcome_are_one_issue():
    summary,_,_=run("What legal actions apply?",
        [pdf("DOC-1-P1")],
        "The violation is proven. The official must prosecute [DOC-1-P1].")
    assert codes(summary).count("LEGAL_OUTCOME_OR_ACTION")==1

def test_officer_review_priority_is_not_violation_severity():
    summary,_,_=run("What legal law applies?",[pdf("DOC-1-P1")],"Pasal 21 [DOC-1-P1].")
    assert summary["priority_is_legal_severity"] is False
    assert summary["status"]=="OFFICER_REVIEW_REQUIRED"

def test_default_legacy_four_checks_remain_unmodified():
    summary,qa,_=run("What legal law applies?",[pdf("DOC-1-P1")],"Pasal 21 [DOC-1-P1].")
    assert len(qa["checks"])==4
    assert [c["id"] for c in qa["checks"]]==[
        "citation_grounding","source_relevance","legal_uncertainty","cross_module_consistency"]
    assert qa["human_accuracy"] is None

def test_nonlegal_question_does_not_show_legal_summary():
    summary,_,_=run("Summarize Riau social posts",
        [{"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
          "source_excerpt":"Riau source"}],"Source [SOCIAL-1].")
    assert summary["applicable"] is False
    assert summary["status"]=="NOT_APPLICABLE"

def test_unknown_reference_is_never_exported_by_summary():
    summary,_,_=run("What legal rule applies?",[pdf("DOC-1-P1")],
                    "Pasal 21 [DOC-1-P1] [DOC-99-P9].")
    assert all("DOC-99-P9" not in issue["source_ids"] for issue in summary["issues"])
    assert "CITATION_INTEGRITY" in codes(summary)

def test_plain_cited_answer_keeps_legal_truth_unverified():
    summary,qa,_=run("What legal rules apply?",
        [pdf("DOC-1-P1",body="Pasal 21.")],"Pasal 21 [DOC-1-P1].")
    assert summary["semantic_entailment_verified"] is False
    assert summary["legal_applicability_verified"] is False
    assert qa["legal_claim_passage_consistency"]["semantic_entailment_verified"] is False

def test_priority_counts_match_distinct_issue_groups():
    summary,_,_=run("What legal rule applies?",
        [pdf("DOC-1-P1",body="Officials must not report.",review="UNREVIEWED")],
        "Officials must report [DOC-1-P1].")
    assert sum(summary["priority_counts"].values())==summary["issue_count"]
    assert len(codes(summary))==len(set(codes(summary)))

def test_status_remains_officer_required_when_no_lexical_gaps():
    doc=pdf("DOC-1-P1",body="Pasal 21.")
    doc.update(legal_version_label="v1",legal_effective_date="2026-01-01")
    summary,_,_=run("What does legal Pasal 21 say?",[doc],"Pasal 21 [DOC-1-P1].")
    assert summary["issue_count"]>=0
    assert summary["status"]=="OFFICER_REVIEW_REQUIRED"
    assert summary["automated_legal_approval"] is False
