"""Conservative, redacted response QA summary for *already authorized* saved replies.

Must be called only after the existing owner + current evidence authorization
and existing deterministic audit. Never stores answer text or generates AI.
Historical chat content is editable and not provenance-authenticated.
"""
from collections import Counter

_KNOWN={"PASS","REVIEW_REQUIRED","NOT_APPLICABLE"}


def summarize_authorized_saved_reply_audit(audit):
    """Summarize the ALREADY run audit, not a new source or a gold benchmark."""
    checks=audit.get("checks") or []
    if not isinstance(checks,list):
        checks=[]
    statuses=Counter()
    review_ids=[]
    for row in checks:
        if not isinstance(row,dict):
            continue
        status=row.get("status")
        if status in _KNOWN:
            statuses[status]+=1
            if status=="REVIEW_REQUIRED":
                name=row.get("id")
                if isinstance(name,str) and name in (
                    "citation_grounding","source_relevance",
                    "legal_uncertainty","cross_module_consistency"
                ):
                    review_ids.append(name)
    # Treat supplemental REVIEW_REQUIRED as a review flag even when all four
    # historical readiness checks pass. Never export arbitrary reason text.
    supplemental_counts=Counter()
    supplemental_review=[]
    allowed_supplemental={
        "citation_inventory_consistency",
        "pdf_quoted_passage_alignment",
        "requested_topic_coverage",
    }
    for row in audit.get("supplemental_checks") or []:
        if not isinstance(row,dict):
            continue
        check_id=row.get("id")
        status=row.get("status")
        if check_id not in allowed_supplemental or status not in _KNOWN:
            continue
        supplemental_counts[status]+=1
        if status=="REVIEW_REQUIRED":
            supplemental_review.append(check_id)
    missing=audit.get("missing_cited_source_kinds") or []
    if not isinstance(missing,list):
        missing=[]
    # These are source-kind labels, never the source text or model answer.
    allowed_kinds={"PDF_KNOWLEDGE","SOCIAL_LISTENING","FORMAL_INTELLIGENCE"}
    missing=sorted({str(kind) for kind in missing if kind in allowed_kinds})
    rejection=audit.get("rejected_unavailable_citation_count")
    if not isinstance(rejection,int) or isinstance(rejection,bool) or rejection<0:
        rejection=0
    issue_count=(audit.get("issue_triage") or {}).get("issue_candidate_count")
    if not isinstance(issue_count,int) or isinstance(issue_count,bool) or issue_count<0:
        issue_count=0
    categories=(audit.get("issue_triage") or {}).get("issue_category_counts") or {}
    issue_category_count=len([key for key,val in categories.items()
                              if isinstance(key,str) and isinstance(val,int)
                              and not isinstance(val,bool) and val>0])
    flagged=bool(review_ids or supplemental_review or missing or rejection or issue_count)
    return {
        "schema":"BAWASLU_SAVED_REPLY_RESPONSE_TRIAGE_V17468",
        "status":"REVIEW_FLAGS_PRESENT" if flagged else "NO_DETERMINISTIC_FLAGS",
        "readiness_check_counts":dict(sorted(statuses.items())),
        "readiness_review_ids":sorted(set(review_ids)),
        "supplemental_check_counts":dict(sorted(supplemental_counts.items())),
        "supplemental_review_ids":sorted(set(supplemental_review)),
        "missing_cited_source_kinds":missing,
        "rejected_citation_count":rejection,
        "issue_candidate_count":issue_count,
        "issue_category_count":issue_category_count,
        "no_flags_is_not_a_quality_pass":True,
        "selected_history_is_user_editable":True,
        "original_model_output_provenance_verified":False,
        "reference_answer_comparison_performed":False,
        "question_completeness_semantically_verified":False,
        "source_truth_verified":False,
        "factual_accuracy_verified":False,
        "legal_currentness_verified":False,
        "human_acceptance":None,
        "model_calls":0,
        "database_writes":0,
    }



def summarize_authorized_saved_reply_batch(results):
    """Redacted aggregate from the existing explicit, permission-scoped batch.

    Missing or malformed triage is counted as UNASSESSED, never as a pass.
    The caller must preserve the original per-selection availability statuses.
    """
    counts=Counter()
    reason_counts=Counter()
    for item in results or []:
        if not isinstance(item,dict):
            counts["UNASSESSED"]+=1
            continue
        status=item.get("status")
        if status!="AUDITED":
            counts["UNASSESSED"]+=1
            continue
        triage=item.get("response_quality_triage")
        if not isinstance(triage,dict):
            counts["UNASSESSED"]+=1
            continue
        state=triage.get("status")
        if state=="REVIEW_FLAGS_PRESENT":
            counts["REVIEW_FLAGS_PRESENT"]+=1
            for reason in triage.get("readiness_review_ids") or []:
                if reason in {"citation_grounding","source_relevance",
                              "legal_uncertainty","cross_module_consistency"}:
                    reason_counts[reason]+=1
        elif state=="NO_DETERMINISTIC_FLAGS":
            counts["NO_DETERMINISTIC_FLAGS"]+=1
        else:
            counts["UNASSESSED"]+=1
    return {
        "schema":"BAWASLU_SAVED_REPLY_BATCH_RESPONSE_TRIAGE_V17472",
        "audited_with_review_flags":counts["REVIEW_FLAGS_PRESENT"],
        "audited_without_detected_flags":counts["NO_DETERMINISTIC_FLAGS"],
        "unassessed_or_unavailable":counts["UNASSESSED"],
        "core_review_reason_occurrences":dict(sorted(reason_counts.items())),
        "no_flags_is_not_a_quality_pass":True,
        "selection_is_not_random_or_representative":True,
        "human_accuracy":None,
        "semantic_entailment_verified":False,
        "historical_model_output_provenance_verified":False,
        "human_acceptance_verified":False,
        "paid_ai_calls":0,
        "database_writes":0,
    }
