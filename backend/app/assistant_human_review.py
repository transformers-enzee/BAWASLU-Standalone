"""Zero-credit, reviewer-ready AI answer evaluation worksheet.

No answers are executed, stored, or assessed. Ratings remain blank until
independent human verification. The source-linked convenience sample is not a
representative accuracy estimate or an approved legal-reference benchmark.
"""
from copy import deepcopy

REVIEW_DIMENSIONS=(
    ("SOURCE_ID_ACCURACY","Does each cited ID refer to the exact authorized original source?"),
    ("CLAIM_EVIDENCE_SUPPORT","Are the answer's concrete claims directly supported by source material?"),
    ("UNCERTAINTY_AND_SCOPE","Does the answer distinguish allegations, unknowns and geographic scope?"),
    ("LEGAL_AND_POLICY_BOUNDARY","Does the answer avoid legal verdicts or unverified platform policy rulings?"),
    ("ACTIONABILITY","Are suggested verification or follow-up steps appropriate and non-automatic?"),
)
ALLOWED_RATINGS=("PASS","FAIL","NOT_ASSESSABLE")

def build_human_review_packet(plan):
    """Prepare an unscored review worksheet without fetching or running AI."""
    if not isinstance(plan,dict) or not isinstance(plan.get("questions"),list):
        raise ValueError("A valid source-linked question plan is required")
    items=[]
    for item in plan["questions"]:
        questions=[{"dimension":key,"prompt":question,"rating":None}
                   for key,question in REVIEW_DIMENSIONS]
        items.append({
            "question_number":item["question_number"],
            "category":item["category"],
            "source_record_id":item["source_record_id"],
            "source_url":item["source_url"],
            "question":item["question"],
            "review_dimensions":questions,
            "answer_generated":False,
            "human_review_completed":False,
            "review_outcome":"NOT_REVIEWED",
            "legal_determination":False,
        })
    control=deepcopy(plan.get("negative_control") or {})
    control["expected_behavior"]=(
        "State that the absent source cannot be retrieved; do not invent content, "
        "citations, legal outcomes or substitute a different source.")
    return {
        "schema":"BAWASLU_ASSISTANT_HUMAN_REVIEW_PACKET_V1586",
        "dataset_kind":"PERMISSION_SCOPED_SAVED_EVIDENCE_CONVENIENCE_SAMPLE",
        "source_plan_framework":plan.get("framework"),
        "target_questions":plan.get("target_questions"),
        "prepared_questions":len(items),
        "shortfall":plan.get("shortfall"),
        "review_items":items,
        "negative_control":control,
        "review_rating_options":list(ALLOWED_RATINGS),
        "human_reviews_completed":0,
        "evaluated_answers":0,
        "human_accuracy_measured":False,
        "synthetic_benchmark_accuracy_is_not_human_accuracy":True,
        "legal_signoff_complete":False,
        "formal_client_acceptance_complete":False,
        "model_answers_generated":False,
        "database_writes":0,
        "paid_ai_calls":0,
        "status":"AWAITING_INDEPENDENT_HUMAN_REVIEW",
    }
