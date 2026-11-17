"""Offline full-answer replay of developer-labeled source-attribution cases.

This fixture pack is not a population sample, real model output, human-rated
accuracy, a legal determination, or a staging database query.
"""
from collections import Counter
from .assistant_grounding import audit_assistant_answer
from .assistant_answer_quality import evaluate_answer_quality

def _social(identifier,sentiment="NEUTRAL"):
    return {"record_id":identifier,"record_type":"SOCIAL_LISTENING",
            "sentiment":sentiment,
            "source_excerpt":"An unverified public discussion about election monitoring."}

def _formal(identifier):
    return {"record_id":identifier,"record_type":"FORMAL_INTELLIGENCE",
            "source_excerpt":"An Inbox review record; verification is not an adjudication."}

def _legal(identifier):
    return {"record_id":identifier,"record_type":"PDF_KNOWLEDGE",
            "document_type":"REGULATION","review_status":"OFFICER_REVIEWED",
            "legal_version_label":"Synthetic draft","legal_effective_date":"2026-01-01",
            "source_excerpt":"Pasal 21 discusses election monitoring rules."}

CROSS_QUESTION="Compare the saved Social Listening source and Intelligence Inbox review."
CASES=(
    {"id":"B01","category":"BOTH_CITED","evidence":[_social("SOCIAL-1"),_formal("INT-1")],
     "answer":"A public post raised concerns [SOCIAL-1]. Inbox review remains pending [INT-1].",
     "cross":"PASS"},
    {"id":"B02","category":"SOCIAL_ONLY_CITED","evidence":[_social("SOCIAL-1"),_formal("INT-1")],
     "answer":"A public post raised concerns [SOCIAL-1]. No formal record is cited.",
     "cross":"REVIEW_REQUIRED"},
    {"id":"B03","category":"FORMAL_ONLY_CITED","evidence":[_social("SOCIAL-1"),_formal("INT-1")],
     "answer":"An Inbox review record exists [INT-1]. Other posts are not cited.",
     "cross":"REVIEW_REQUIRED"},
    {"id":"B04","category":"NO_DISPLAYED_CITATION","evidence":[_social("SOCIAL-1"),_formal("INT-1")],
     "answer":"Monitoring records are available, but none are cited.",
     "cross":"REVIEW_REQUIRED"},
    {"id":"B05","category":"UNSELECTED_CITATION","evidence":[_social("SOCIAL-1"),_formal("INT-1")],
     "answer":"A public post was found [SOCIAL-1]. Formal case [INT-999] is unavailable.",
     "cross":"REVIEW_REQUIRED","rejected":1},
    {"id":"B06","category":"MISSING_FORMAL_SELECTION","evidence":[_social("SOCIAL-1")],
     "answer":"Only a saved public post is shown [SOCIAL-1].",
     "cross":"REVIEW_REQUIRED"},
    {"id":"B07","category":"MISSING_SOCIAL_SELECTION","evidence":[_formal("INT-1")],
     "answer":"Only an Inbox review is shown [INT-1].",
     "cross":"REVIEW_REQUIRED"},
    {"id":"B08","category":"MULTIPLE_CITED_SOURCES","evidence":[_social("SOCIAL-1"),_social("SOCIAL-2"),_formal("INT-1")],
     "answer":"First post [SOCIAL-1]. Second post [SOCIAL-2]. Inbox review [INT-1].",
     "cross":"PASS"},
    {"id":"B09","category":"CONFLICTING_DUPLICATE_SOCIAL","evidence":[_social("SOCIAL-1","POSITIVE"),
      _social("SOCIAL-1","NEGATIVE"),_formal("INT-1")],
     "answer":"Public source [SOCIAL-1]. Inbox review [INT-1].",
     "cross":"REVIEW_REQUIRED","conflicts":1},
    {"id":"B10","category":"LEGAL_NOT_FORMAL_INBOX","evidence":[_social("SOCIAL-1"),_legal("DOC-1-P1")],
     "answer":"A public post [SOCIAL-1]. An electoral-law PDF [DOC-1-P1].",
     "cross":"REVIEW_REQUIRED"},
    {"id":"B11","category":"SOCIAL_FORMAL_ASSERTION","evidence":[_social("SOCIAL-1"),_formal("INT-1")],
     "answer":"BAWASLU confirmed an electoral violation [SOCIAL-1]. Inbox information [INT-1].",
     "cross":"PASS","issue":"FORMAL_OUTCOME_SOCIAL_ONLY"},
    {"id":"B12","category":"PLATFORM_POLICY_BOUNDARY","evidence":[_social("SOCIAL-1"),_formal("INT-1"),_legal("DOC-1-P1")],
     "answer":"A public post [SOCIAL-1]. An Inbox record [INT-1]. Instagram violates platform policy [DOC-1-P1].",
     "cross":"PASS","issue":"PLATFORM_POLICY_BOUNDARY"},
)

def run_full_answer_replay(cases=CASES):
    """Replay bounded, explicit scenarios through the production audit pipeline."""
    outcomes=[]
    category_counts=Counter()
    for case in cases:
        visible,cited,ground=audit_assistant_answer(
            CROSS_QUESTION,case["evidence"],case["answer"],
            profile="CROSS_MODULE_REVIEW",language="en")
        qa=evaluate_answer_quality(
            CROSS_QUESTION,case["evidence"],visible,cited,
            profile="CROSS_MODULE_REVIEW",grounding=ground)
        cross=next(x for x in qa["checks"] if x["id"]=="cross_module_consistency")
        issues=[item["code"] for item in qa["legal_review_summary"]["issues"]]
        expected_issue=case.get("issue")
        matched=(cross["status"]==case["cross"] and
                 (expected_issue is None or expected_issue in issues) and
                 ground["rejected_unavailable_citations"]==case.get("rejected",0) and
                 cross.get("duplicate_sentiment_conflicts",0)==case.get("conflicts",0))
        category_counts[case["category"]]+=1
        outcomes.append({"id":case["id"],"category":case["category"],
                         "expected_cross_module_status":case["cross"],
                         "observed_cross_module_status":cross["status"],
                         "displayed_cited_ids":cited,
                         "missing_citation_kinds":cross.get("missing_citation_kinds",[]),
                         "observed_review_issue_codes":issues,
                         "expected_review_issue":expected_issue,
                         "matched":matched,"synthetic_only":True})
    return {"schema":"BAWASLU_FULL_ANSWER_SYNTHETIC_REPLAY_V1607",
            "dataset_kind":"DEVELOPER_LABELED_SYNTHETIC_FULL_ANSWERS",
            "scenarios":len(outcomes),
            "cases_matched":sum(x["matched"] for x in outcomes),
            "cases_failed":sum(not x["matched"] for x in outcomes),
            "category_counts":dict(category_counts),
            "results":outcomes,
            "real_model_responses_evaluated":0,
            "human_gold_answers_evaluated":0,
            "human_accuracy_measured":False,
            "legal_applicability_verified":False,
            "formal_client_acceptance_verified":False,
            "statistically_representative":False,
            "database_writes":0,"paid_ai_calls":0,
            "status":"SYNTHETIC_PIPELINE_REGRESSION_ONLY"}
