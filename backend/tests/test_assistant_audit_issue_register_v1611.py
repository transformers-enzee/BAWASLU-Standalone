"""Automation flags candidates only, with no confirmation or raw answer storage."""
import json
from app.assistant_audit_issue_register import classify_answer_audit
from app.assistant_eval_sampling import SavedAnswerAuditRequest,build_saved_answer_audit,MixedAnswerAuditRequest,build_mixed_answer_audit

def test_issue_categories_and_distinct_source_checks():
    q={"checks":[{"id":"citation_grounding","status":"REVIEW_REQUIRED"},
                 {"id":"cross_module_consistency","status":"REVIEW_REQUIRED"}],
       "legal_review_summary":{"issues":[{"code":"PLATFORM_POLICY_BOUNDARY"},
                                         {"code":"FORMAL_OUTCOME_SOCIAL_ONLY"}]}}
    x=classify_answer_audit(q,{"rejected_unavailable_citations":1},
      ["SOCIAL-7"],{"SOCIAL-7":"SOCIAL_LISTENING","INT-1":"FORMAL_INTELLIGENCE"})
    pairs={(r["category"],r["code"]) for r in x["issue_candidates"]}
    assert ("CITATION_INTEGRITY","UNAVAILABLE_DISPLAYED_REFERENCE") in pairs
    assert ("CROSS_MODULE_COVERAGE","SELECTED_UNCITED_FORMAL_INTELLIGENCE") in pairs
    assert ("PLATFORM_POLICY_AUTHORITY","PLATFORM_POLICY_BOUNDARY") in pairs
    assert ("FORMAL_DECISION_PROVENANCE","FORMAL_OUTCOME_SOCIAL_ONLY") in pairs
    assert len(pairs)==x["issue_candidate_count"]
    assert all(r["human_confirmed"] is False for r in x["issue_candidates"])
    assert x["observed_model_accuracy"] is None and not x["legal_approval_granted"]

def test_no_issue_does_not_equal_human_accuracy():
    x=classify_answer_audit({"checks":[]},{},["SOCIAL-7"],
      {"SOCIAL-7":"SOCIAL_LISTENING"})
    assert x["issue_candidate_count"]==0
    assert x["human_review_completed"] is False

def test_saved_source_audit_carries_only_sanitized_warnings():
    x=build_saved_answer_audit([{"posts":[{"result_id":"7","canonical_source_id":"social:7",
      "message_original":"Private and unverified post text"}]}],
      SavedAnswerAuditRequest(source_ids=["SOCIAL-7"],question="What does this say?",
                              answer="An unsupported claim [SOCIAL-999]."))
    assert x["issue_triage"]["issue_candidate_count"]>=1
    assert "Private and unverified post text" not in json.dumps(x)
    assert "An unsupported claim" not in json.dumps(x)
    assert x["human_accuracy"] is None

def test_mixed_audit_missing_formal_kind_becomes_specific_candidate():
    rows=[{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
           "source_excerpt":"Unverified post"},
          {"record_id":"INT-1","record_type":"FORMAL_INTELLIGENCE",
           "source_excerpt":"Pending case review"}]
    x=build_mixed_answer_audit(rows,MixedAnswerAuditRequest(
        source_ids=["SOCIAL-7","INT-1"],question="Compare formal and social evidence",
        answer="Social discussion [SOCIAL-7]."))
    assert x["issue_triage"]["issue_category_counts"]["CROSS_MODULE_COVERAGE"]>=1
    assert x["issue_triage"]["human_confirmed_issue_count"]==0
    assert x["human_accuracy"] is None
