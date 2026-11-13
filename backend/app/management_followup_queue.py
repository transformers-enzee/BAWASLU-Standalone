"""Read-only authorized management follow-up queue.

Inputs are already jurisdiction-filtered casework, the latest report per case,
and source-review events inside the reporting window. A missing window event is
NOT proof that the source was never reviewed. No additional DB query, AI calls,
automatic case actions, authority assumptions, or legal conclusions.
"""
from collections import Counter
from .management_investigation_readiness import classify_case_readiness

_LEVEL={"P1":0,"P2":1,"P3":2}
_ACTIONS={
    "RECEIVING_TEAM_ACCEPTANCE",
    "CASE_INFORMATION_FOLLOWUP",
    "SOURCE_REVIEW_RECHECK",
    "CHECK_HISTORICAL_SOURCE_REVIEW",
    "SUBMIT_OR_REVISE_LATEST_REPORT",
    "CREATE_OFFICER_REPORT",
    "INDEPENDENT_REPORT_REVIEW",
    "RECONCILE_CASE_REPORT_STATUS",
}

def management_followup_queue(cases,latest_by_case,transitions):
    events={}
    for event in sorted(transitions,key=lambda row:row.id):
        if event.action=="SOURCE_REVIEW_RECORDED":
            events[event.case_id]=event
    items=[]
    closed_excluded=0
    approved_excluded=0
    for case in cases:
        if case.status=="CLOSED":
            closed_excluded+=1
            continue
        report=latest_by_case.get(case.id)
        report_status=str(report.status) if report else "NO_REPORT"
        review=events.get(case.id)
        group,reason,step,case_status,report_status,observed,checked=classify_case_readiness(
            case,report,review)
        # A submitted report is not ready for independent sign-off simply
        # because its report status says SUBMITTED. Source-review ambiguity
        # takes precedence, consistently with the readiness dashboard.
        if group=="WORKFLOW_COMPLETE":
            approved_excluded+=1
            continue
        if reason=="APPROVED_REPORT_WITH_UNRESOLVED_CASE_STATUS":
            code,level,actor="RECONCILE_CASE_REPORT_STATUS","P1","AUTHORIZED_CASEWORK_REVIEWER"
        elif group=="EVIDENCE_RECHECK":
            code,level,actor="SOURCE_REVIEW_RECHECK","P1","ASSIGNED_OFFICER"
        elif group=="REVIEW_HISTORY_CHECK":
            code,level,actor="CHECK_HISTORICAL_SOURCE_REVIEW","P2","ASSIGNED_OFFICER"
        elif group=="INDEPENDENT_REVIEW":
            code,level,actor="INDEPENDENT_REPORT_REVIEW","P1","INDEPENDENT_REVIEWER"
        elif reason=="RECEIVING_OFFICER_NOT_YET_ACCEPTED":
            code,level,actor="RECEIVING_TEAM_ACCEPTANCE","P1","RECEIVING_TEAM"
        elif reason=="CASE_INFORMATION_REQUESTED":
            code,level,actor="CASE_INFORMATION_FOLLOWUP","P1","ASSIGNED_OFFICER"
        elif group=="OFFICER_ACTION" and report_status in {"DRAFT","RETURNED"}:
            code,level,actor="SUBMIT_OR_REVISE_LATEST_REPORT","P2","ASSIGNED_OFFICER"
        elif group=="OFFICER_ACTION" and report_status=="NO_REPORT":
            code,level,actor="CREATE_OFFICER_REPORT","P2","ASSIGNED_OFFICER"
        else:
            # Do not claim a clear approval or confidently route an unknown
            # workflow state from a partially observed time window.
            code,level,actor="RECONCILE_CASE_REPORT_STATUS","P2","AUTHORIZED_CASEWORK_REVIEWER"
        if code not in _ACTIONS:
            continue
        cid=int(case.id)
        items.append({
            "case_id":cid,
            "priority":level,
            "action_code":code,
            "responsible_role_hint":actor,
            "case_status":str(case.status),
            "latest_report_status":report_status,
            "latest_source_review_observed_in_window":observed,
            "aligned_readiness_group":group,
            "aligned_readiness_reason":reason,
            "reconciliation_is_workflow_only":True,
            "source_review_attested_in_window":checked,
            "casework_url":f"/inbox?casework=1&case_id={cid}&tab=reports",
            "authorized_case_only":True,
            "recommended_action_is_assignment":False,
            "legal_outcome_confirmed":False,
        })
    items.sort(key=lambda x:(_LEVEL[x["priority"]],x["action_code"],x["case_id"]))
    counts=Counter(row["action_code"] for row in items)
    return {
        "schema":"BAWASLU_AUTHORIZED_FOLLOWUP_QUEUE_V1536",
        "case_population":"AUTHORIZED_ASSIGNMENTS_CREATED_IN_SELECTED_UTC_PERIOD",
        "status":"READ_ONLY_OFFICER_ACTION_HINTS",
        "classification_basis":"SHARED_INVESTIGATION_READINESS_V1539",
        "independent_review_requires_window_source_attestation":True,
        "authorized_case_population":len(cases),
        "attention_count":len(items),
        "priority_counts":{level:sum(x["priority"]==level for x in items)
                           for level in _LEVEL},
        "action_counts":dict(sorted(counts.items())),
        "items":items[:12],
        "preview_limit":12,
        "preview_is_sample":len(items)>12,
        "closed_cases_excluded":closed_excluded,
        "approved_report_cases_without_open_followup":approved_excluded,
        "source_review_scope":"LATEST_RECORDED_EVENT_WITHIN_REPORTING_WINDOW",
        "historical_source_review_may_exist":True,
        "casework_links_recheck_permissions":True,
        "source_truth_verified":False,
        "legal_verdict_confirmed":False,
        "platform_violation_confirmed":False,
        "formal_approval_created":False,
        "automatic_casework_actions_created":False,
        "additional_database_queries":0,
        "paid_provider_called":False,
    }
