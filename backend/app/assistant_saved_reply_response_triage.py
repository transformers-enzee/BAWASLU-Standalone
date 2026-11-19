"""Conservative, redacted response QA summary for *already authorized* saved replies.

Must be called only after the existing owner + current evidence authorization
and existing deterministic audit. Never stores answer text or generates AI.
Historical chat content is editable and not provenance-authenticated.
"""
from collections import Counter

_KNOWN={"PASS","REVIEW_REQUIRED","NOT_APPLICABLE"}
_CORE={"citation_grounding","source_relevance",
       "legal_uncertainty","cross_module_consistency"}
_SUPPLEMENTAL={"citation_inventory_consistency",
               "pdf_quoted_passage_alignment","requested_topic_coverage"}


def summarize_authorized_saved_reply_audit(audit):
    """Summarize the ALREADY run audit, not a new source or a gold benchmark."""
    checks=audit.get("checks") or []
    if not isinstance(checks,list):
        checks=[]
    statuses=Counter()
    review_ids=[]
    seen_core=set()
    duplicate_core=False
    for row in checks:
        if not isinstance(row,dict):
            continue
        status=row.get("status")
        name=row.get("id")
        if not isinstance(name,str) or not isinstance(status,str) or name not in _CORE or status not in _KNOWN:
            continue
        if name in seen_core:
            duplicate_core=True
            continue
        seen_core.add(name)
        statuses[status]+=1
        if status=="REVIEW_REQUIRED":
            review_ids.append(name)
    # Treat supplemental REVIEW_REQUIRED as a review flag even when all four
    # historical readiness checks pass. Never export arbitrary reason text.
    supplemental_counts=Counter()
    supplemental_review=[]
    seen_supplemental=set()
    duplicate_supplemental=False
    for row in audit.get("supplemental_checks") or []:
        if not isinstance(row,dict):
            continue
        check_id=row.get("id")
        status=row.get("status")
        if not isinstance(check_id,str) or not isinstance(status,str) or check_id not in _SUPPLEMENTAL or status not in _KNOWN:
            continue
        if check_id in seen_supplemental:
            duplicate_supplemental=True
            continue
        seen_supplemental.add(check_id)
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
    diagnostics_complete=(seen_core==_CORE and seen_supplemental==_SUPPLEMENTAL
                          and not duplicate_core and not duplicate_supplemental)
    status=("REVIEW_FLAGS_PRESENT" if flagged else
            "INCOMPLETE_DIAGNOSTICS" if not diagnostics_complete else
            "NO_DETERMINISTIC_FLAGS")
    return {
        "schema":"BAWASLU_SAVED_REPLY_RESPONSE_TRIAGE_V17468",
        "status":status,
        "diagnostics_complete":diagnostics_complete,
        "human_review_route":(
            "REVIEW_FLAGS_AND_MISSING_CHECKS" if flagged and not diagnostics_complete else
            "REVIEW_FLAGGED_SOURCE_CLAIMS" if flagged else
            "COMPLETE_HEURISTIC_SPOT_CHECK" if diagnostics_complete else
            "REPEAT_INCOMPLETE_QA"
        ),
        "core_missing_check_ids":sorted(_CORE-seen_core),
        "supplemental_missing_check_ids":sorted(_SUPPLEMENTAL-seen_supplemental),
        "core_check_count":len(seen_core),
        "supplemental_check_count":len(seen_supplemental),
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
    incomplete_flagged=0
    complete_flagged=0
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
            if triage.get("diagnostics_complete") is True:
                complete_flagged+=1
            else:
                incomplete_flagged+=1
            for reason in triage.get("readiness_review_ids") or []:
                if isinstance(reason,str) and reason in {"citation_grounding","source_relevance",
                              "legal_uncertainty","cross_module_consistency"}:
                    reason_counts[reason]+=1
            for reason in triage.get("supplemental_review_ids") or []:
                if isinstance(reason,str) and reason in {"citation_inventory_consistency",
                              "pdf_quoted_passage_alignment",
                              "requested_topic_coverage"}:
                    reason_counts[reason]+=1
        elif state=="NO_DETERMINISTIC_FLAGS" and triage.get("diagnostics_complete") is True:
            # Never accept a claimed clean status without explicit proof
            # that both the core and supplemental diagnostic sets completed.
            counts["NO_DETERMINISTIC_FLAGS"]+=1
        else:
            counts["UNASSESSED"]+=1
    return {
        "schema":"BAWASLU_SAVED_REPLY_BATCH_RESPONSE_TRIAGE_V17472",
        "audited_with_review_flags":counts["REVIEW_FLAGS_PRESENT"],
        "review_flags_with_complete_diagnostics":complete_flagged,
        "review_flags_with_incomplete_diagnostics":incomplete_flagged,
        "audited_without_detected_flags":counts["NO_DETERMINISTIC_FLAGS"],
        "unassessed_or_unavailable":counts["UNASSESSED"],
        "review_reason_occurrences":dict(sorted(reason_counts.items())),
        "core_review_reason_occurrences":dict(sorted(
            (key,value) for key,value in reason_counts.items()
            if key in {"citation_grounding","source_relevance",
                       "legal_uncertainty","cross_module_consistency"})),
        "no_flags_is_not_a_quality_pass":True,
        "selection_is_not_random_or_representative":True,
        "human_accuracy":None,
        "semantic_entailment_verified":False,
        "historical_model_output_provenance_verified":False,
        "human_acceptance_verified":False,
        "paid_ai_calls":0,
        "database_writes":0,
    }
