"""Redacted human-review worksheet for user-selected, authorized Assistant replies.

Input MUST be the result of audit_owned_saved_reply_batch after ownership and
fresh source authorization. No model calls, database writes, or automatic ratings.
An audited result is a review candidate, not a correct or authentic model answer.
"""
import re
from collections import Counter

_UUID=re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}

DIMENSIONS=(
    "SOURCE_ID_ACCURACY",
    "CLAIM_EVIDENCE_SUPPORT",
    "QUESTION_COMPLETENESS",
    "UNCERTAINTY_AND_SCOPE",
    "LEGAL_AND_POLICY_BOUNDARY",
    "ACTIONABILITY",
)
_RATINGS=("PASS","FAIL","NOT_ASSESSABLE")


def build_authorized_saved_reply_review_packet(batch):
    """Provide blank review tasks without reproducing answers or source text."""
    if not isinstance(batch,dict) or batch.get("selection_method")!="EXPLICIT_USER_SELECTED_REPLIES":
        raise ValueError("A permission-scoped explicit-selection batch audit is required")
    rows=batch.get("results")
    if not isinstance(rows,list) or not 1<=len(rows)<=5:
        raise ValueError("Expected one to five authorized reply selections")
    if batch.get("requested")!=len(rows):
        raise ValueError("Batch selection count does not match audit results")
    tasks=[]
    statuses=Counter()
    selected_keys=set()
    for item in rows:
        if not isinstance(item,dict):
            raise ValueError("Invalid batch audit result")
        status=item.get("status")
        if status not in {"AUDITED","SOURCE_UNAVAILABLE","UNAVAILABLE","INELIGIBLE"}:
            raise ValueError("Unsupported authorization or eligibility result")
        statuses[status]+=1
        if status!="AUDITED":
            continue
        triage=item.get("response_quality_triage")
        if not isinstance(triage,dict):
            raise ValueError("Audited reply requires response-quality triage")
        if triage.get("status") not in (
            "REVIEW_FLAGS_PRESENT","NO_DETERMINISTIC_FLAGS","INCOMPLETE_DIAGNOSTICS"):
            raise ValueError("Audited reply has an unsupported triage state")
        thread_id=item.get("thread_id")
        index=item.get("answer_message_index")
        if not isinstance(thread_id,str) or not _UUID.fullmatch(thread_id) or not isinstance(index,int) or isinstance(index,bool) or not 1<=index<=59:
            raise ValueError("Invalid selected saved-reply identifier")
        key=(thread_id,index)
        if key in selected_keys:
            raise ValueError("Duplicate audited saved-reply selection")
        selected_keys.add(key)
        tasks.append({
            "thread_id":thread_id,
            "answer_message_index":index,
            "triage_status":triage["status"],
            "diagnostics_complete":triage.get("diagnostics_complete") is True,
            "recommended_action":triage.get("human_review_route")
                if triage.get("human_review_route") in {
                    "REVIEW_FLAGS_AND_MISSING_CHECKS",
                    "REVIEW_FLAGGED_SOURCE_CLAIMS",
                    "COMPLETE_HEURISTIC_SPOT_CHECK",
                    "REPEAT_INCOMPLETE_QA",
                } else "VERIFY_SOURCE_AND_ANSWER_MANUALLY",
            "review_dimensions":[{"dimension":name,"rating":None,"reviewer_note":None}
                                 for name in DIMENSIONS],
            "source_access_recheck_required_at_review_time":True,
            "review_completed":False,
            "model_output_provenance_verified":False,
            "legal_signoff_verified":False,
        })
    return {
        "schema":"BAWASLU_AUTHORIZED_SAVED_REPLY_REVIEW_PACKET_V17488",
        "selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
        "review_sample_is_representative":False,
        "requested_replies":len(rows),
        "review_ready_replies":len(tasks),
        "ineligible_or_unavailable_replies":len(rows)-len(tasks),
        "source_access_checked_for_audited_replies":True,
        "source_access_recheck_required_before_review":True,
        "items":tasks,
        "rating_options":list(_RATINGS),
        "actual_answer_text_included":False,
        "raw_evidence_text_included":False,
        "human_ratings_prepopulated":False,
        "human_review_completed":False,
        "actual_model_accuracy_measured":False,
        "legal_signoff_complete":False,
        "generation_calls":0,
        "database_writes":0,
    }
)

DIMENSIONS=(
    "SOURCE_ID_ACCURACY",
    "CLAIM_EVIDENCE_SUPPORT",
    "QUESTION_COMPLETENESS",
    "UNCERTAINTY_AND_SCOPE",
    "LEGAL_AND_POLICY_BOUNDARY",
    "ACTIONABILITY",
)
_RATINGS=("PASS","FAIL","NOT_ASSESSABLE")


def build_authorized_saved_reply_review_packet(batch):
    """Provide blank review tasks without reproducing answers or source text."""
    if not isinstance(batch,dict) or batch.get("selection_method")!="EXPLICIT_USER_SELECTED_REPLIES":
        raise ValueError("A permission-scoped explicit-selection batch audit is required")
    rows=batch.get("results")
    if not isinstance(rows,list) or not 1<=len(rows)<=5:
        raise ValueError("Expected one to five authorized reply selections")
    if batch.get("requested")!=len(rows):
        raise ValueError("Batch selection count does not match audit results")
    tasks=[]
    statuses=Counter()
    for item in rows:
        if not isinstance(item,dict):
            raise ValueError("Invalid batch audit result")
        status=item.get("status")
        if status not in {"AUDITED","SOURCE_UNAVAILABLE","UNAVAILABLE","INELIGIBLE"}:
            raise ValueError("Unsupported authorization or eligibility result")
        statuses[status]+=1
        if status!="AUDITED":
            continue
        triage=item.get("response_quality_triage")
        if not isinstance(triage,dict):
            raise ValueError("Audited reply requires response-quality triage")
        if triage.get("status") not in (
            "REVIEW_FLAGS_PRESENT","NO_DETERMINISTIC_FLAGS","INCOMPLETE_DIAGNOSTICS"):
            raise ValueError("Audited reply has an unsupported triage state")
        thread_id=item.get("thread_id")
        index=item.get("answer_message_index")
        if not isinstance(thread_id,str) or len(thread_id)!=36 or not isinstance(index,int) or isinstance(index,bool) or not 1<=index<=59:
            raise ValueError("Invalid selected saved-reply identifier")
        tasks.append({
            "thread_id":thread_id,
            "answer_message_index":index,
            "triage_status":triage["status"],
            "diagnostics_complete":triage.get("diagnostics_complete") is True,
            "recommended_action":triage.get("human_review_route")
                if triage.get("human_review_route") in {
                    "REVIEW_FLAGS_AND_MISSING_CHECKS",
                    "REVIEW_FLAGGED_SOURCE_CLAIMS",
                    "COMPLETE_HEURISTIC_SPOT_CHECK",
                    "REPEAT_INCOMPLETE_QA",
                } else "VERIFY_SOURCE_AND_ANSWER_MANUALLY",
            "review_dimensions":[{"dimension":name,"rating":None,"reviewer_note":None}
                                 for name in DIMENSIONS],
            "source_access_recheck_required_at_review_time":True,
            "review_completed":False,
            "model_output_provenance_verified":False,
            "legal_signoff_verified":False,
        })
    return {
        "schema":"BAWASLU_AUTHORIZED_SAVED_REPLY_REVIEW_PACKET_V17488",
        "selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
        "review_sample_is_representative":False,
        "requested_replies":len(rows),
        "review_ready_replies":len(tasks),
        "ineligible_or_unavailable_replies":len(rows)-len(tasks),
        "source_access_checked_for_audited_replies":True,
        "source_access_recheck_required_before_review":True,
        "items":tasks,
        "rating_options":list(_RATINGS),
        "actual_answer_text_included":False,
        "raw_evidence_text_included":False,
        "human_ratings_prepopulated":False,
        "human_review_completed":False,
        "actual_model_accuracy_measured":False,
        "legal_signoff_complete":False,
        "generation_calls":0,
        "database_writes":0,
    }
