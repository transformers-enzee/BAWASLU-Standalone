"""Workflow-only investigation readiness for authorized Command Centre casework.

Uses records already loaded and permission-scoped by management_reporting.
Its category is a review-routing hint, NEVER a legal or factual finding.
A source-review event absent from this reporting window may exist earlier.
No database reads, paid inference, assignment, approval, or takedown actions.
"""
from collections import Counter
from .casework import _json

_GROUPS=("EVIDENCE_RECHECK","REVIEW_HISTORY_CHECK","OFFICER_ACTION",
         "INDEPENDENT_REVIEW","WORKFLOW_COMPLETE","OTHER_FOLLOWUP")
_ORDER={k:i for i,k in enumerate(_GROUPS)}
_REVIEW_CODES={
    "RECHECK_ORIGINAL_SOURCE","INSPECT_EARLIER_AUDIT_HISTORY",
    "RECEIVING_OFFICER_ACCEPTANCE","COMPLETE_CASE_INFORMATION",
    "OFFICER_REPORT_DECISION","INDEPENDENT_REVIEW_OF_SUBMITTED_REPORT",
    "VERIFY_UNRECOGNIZED_CASE_STATE","NO_AUTOMATED_ACTION",
}

def classify_case_readiness(case,report,event):
    """Single source of truth for officer review routing and management readiness.

    Observed attestation is a workflow event in the selected report period,
    not an assessment of legal truth or evidence authenticity.
    """
    report_status=str(report.status) if report else "NO_REPORT"
    case_status=str(case.status or "UNKNOWN")
    details=_json(event.details_json,{}) if event else {}
    if not isinstance(details,dict):
        details={}
    observed=bool(event)
    attested=bool(event and details.get("status")=="SOURCE_CHECKED"
        and details.get("original_source_opened") is True
        and details.get("source_type")==case.source_type
        and str(details.get("source_id"))==str(case.source_id)
        and details.get("source_url")==case.source_url)
    if case_status=="CLOSED":
        group,reason,step="WORKFLOW_COMPLETE","CASE_CLOSED_WORKFLOW","NO_AUTOMATED_ACTION"
    elif report_status=="APPROVED":
        if case_status in {"OPEN","ASSIGNED","NEEDS_INFORMATION"}:
            group,reason,step="OTHER_FOLLOWUP","APPROVED_REPORT_WITH_UNRESOLVED_CASE_STATUS","VERIFY_UNRECOGNIZED_CASE_STATE"
        else:
            group,reason,step="WORKFLOW_COMPLETE","LATEST_REPORT_WORKFLOW_APPROVED","NO_AUTOMATED_ACTION"
    elif report_status=="SUBMITTED":
        if attested:
            group,reason,step="INDEPENDENT_REVIEW","SUBMITTED_WITH_WINDOW_SOURCE_ATTESTATION","INDEPENDENT_REVIEW_OF_SUBMITTED_REPORT"
        elif observed:
            group,reason,step="EVIDENCE_RECHECK","SUBMITTED_WITH_UNRESOLVED_WINDOW_SOURCE_REVIEW","RECHECK_ORIGINAL_SOURCE"
        else:
            group,reason,step="REVIEW_HISTORY_CHECK","SUBMITTED_WITHOUT_WINDOW_SOURCE_REVIEW_EVENT","INSPECT_EARLIER_AUDIT_HISTORY"
    elif case_status in {"OPEN","ASSIGNED"}:
        group,reason,step="OFFICER_ACTION","RECEIVING_OFFICER_NOT_YET_ACCEPTED","RECEIVING_OFFICER_ACCEPTANCE"
    elif case_status=="NEEDS_INFORMATION":
        group,reason,step="OFFICER_ACTION","CASE_INFORMATION_REQUESTED","COMPLETE_CASE_INFORMATION"
    elif observed and not attested:
        group,reason,step="EVIDENCE_RECHECK","LATEST_WINDOW_SOURCE_CHECK_NOT_ATTESTED","RECHECK_ORIGINAL_SOURCE"
    elif not observed:
        group,reason,step="REVIEW_HISTORY_CHECK","NO_WINDOW_SOURCE_REVIEW_EVENT","INSPECT_EARLIER_AUDIT_HISTORY"
    elif attested and report_status in {"NO_REPORT","DRAFT","RETURNED"}:
        group,reason,step="OFFICER_ACTION","SOURCE_CHECK_LOGGED_REPORT_DECISION_PENDING","OFFICER_REPORT_DECISION"
    else:
        group,reason,step="OTHER_FOLLOWUP","WORKFLOW_STATUS_NOT_CLASSIFIED","VERIFY_UNRECOGNIZED_CASE_STATE"
    assert step in _REVIEW_CODES
    return group,reason,step,case_status,report_status,observed,attested


def investigation_readiness_board(cases,latest_by_case,transitions):
    """One conservative classification per case, including workflow-complete cases.

    The preview only contains pending review candidates and is a capped
    subset; group counts always reflect the FULL authorized case cohort.
    """
    source_events={}
    for event in sorted(transitions,key=lambda item:item.id):
        if event.action=="SOURCE_REVIEW_RECORDED":
            source_events[event.case_id]=event
    counts=Counter()
    categories=Counter()
    preview=[]
    for case in cases:
        report=latest_by_case.get(case.id)
        event=source_events.get(case.id)
        group,reason,step,case_status,report_status,observed,attested=classify_case_readiness(
            case,report,event)
        counts[group]+=1
        categories[reason]+=1
        if group=="WORKFLOW_COMPLETE":
            continue
        cid=int(case.id)
        preview.append({
            "case_id":cid,"group":group,"reason_code":reason,
            "next_check_code":step,
            "case_status":case_status,"latest_report_status":report_status,
            "source_review_observed_in_window":observed,
            "source_check_attested_in_window":attested,
            "source_check_basis":"AUDIT_EVENT_IN_SELECTED_UTC_REPORT_WINDOW",
            "casework_url":f"/inbox?casework=1&case_id={cid}&tab=reports",
            "casework_permissions_rechecked_on_navigation":True,
            "prepared_for_legal_determination":False,
            "ready_for_independent_review_is_legal_approval":False,
        })
    preview.sort(key=lambda x:(_ORDER[x["group"]],x["case_id"]))
    all_counts={group:counts[group] for group in _GROUPS}
    return {
        "schema":"BAWASLU_INVESTIGATION_READINESS_V1537",
        "scope":"AUTHORIZED_CASES_CREATED_IN_SELECTED_UTC_PERIOD",
        "review_categories_not_legal_severity":True,
        "authorized_case_count":len(cases),
        "review_attention_count":len(preview),
        "group_counts":all_counts,
        "reason_counts":dict(sorted(categories.items())),
        "preview":preview[:12],
        "preview_limit":12,
        "preview_is_sample":len(preview)>12,
        "group_counts_cover_full_authorized_cohort":True,
        "latest_report_version_only":True,
        "missing_window_source_event_does_not_mean_never_reviewed":True,
        "source_truth_verified":False,
        "legal_violation_confirmed":False,
        "platform_violation_confirmed":False,
        "independent_review_approved":False,
        "any_case_assigned_or_updated":False,
        "any_takedown_requested":False,
        "database_queries":0,
        "paid_ai_calls":0,
    }
