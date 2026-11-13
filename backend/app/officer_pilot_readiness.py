"""Authorized officer-pilot evidence, never formal or automatic acceptance.

Uses only already-authorized casework in the selected UTC reporting window.
Stage observations are historical workflow evidence, NOT officer certification.
No DB calls, paid AI, casework changes, or raw source/audit-note exposure.
"""
from collections import defaultdict
from .casework import _acceptance_trace

_STAGES=("source_linked","receiving_officer_accepted","original_source_checked",
         "latest_report_submitted","independent_report_approval")


def officer_pilot_case_rows(cases,latest_by_case,transitions):
    """One evidence-minimized worksheet row per authorized case, not per event.

    The calling endpoint MUST permission-scope cases before calling this.
    Only the chosen report window's audit events are visible in this view.
    """
    authorized={int(case.id):case for case in cases}
    selected_events=defaultdict(list)
    for item in sorted(transitions,key=lambda event:event.id):
        if item.case_id in authorized:
            selected_events[item.case_id].append(item)
    rows=[]
    for case_id in sorted(authorized):
        case=authorized[case_id]
        report=latest_by_case.get(case_id)
        trace=_acceptance_trace(case,selected_events[case_id],[report] if report else [])
        stages={step["key"]:bool(step["done"]) for step in trace["steps"]
                if step["key"] in _STAGES}
        stages={key:stages.get(key,False) for key in _STAGES}
        missing=[key for key in _STAGES if not stages[key]]
        rows.append({
            "case_id":case_id,
            "case_status":str(case.status or "UNKNOWN")[:48],
            "latest_report_status":str(report.status)[:48] if report else "NO_REPORT",
            "observed_stages":stages,
            "observed_stage_count":sum(stages.values()),
            "all_five_stages_observed":not missing,
            "next_unobserved_step":missing[0] if missing else None,
            "audit_event_window_limited":bool(trace["event_window_limited"]),
            "historical_events_outside_period_may_exist":True,
            "casework_url":f"/inbox?casework=1&case_id={case_id}&tab=reports",
            "casework_permission_checked_at_request":True,
            "casework_permission_rechecked_on_navigation":True,
            "source_truth_verified":False,
            "legal_verdict_confirmed":False,
            "officer_signoff_received":False,
            "independent_acceptance_received":False,
            "automatic_casework_actions_created":False,
        })
    return rows


def officer_pilot_readiness(cases,latest_by_case,transitions):
    rows=officer_pilot_case_rows(cases,latest_by_case,transitions)
    size=len(rows)
    counts={key:sum(int(row["observed_stages"][key]) for row in rows)
            for key in _STAGES}
    full_trace_cases=sum(int(row["all_five_stages_observed"]) for row in rows)
    return {
        "schema":"BAWASLU_OFFICER_PILOT_EVIDENCE_V1540",
        "authorized_case_count":size,
        "real_casework_available_in_scope":bool(size),
        "stage_counts":counts,
        "five_stage_observed_case_count":full_trace_cases,
        "cases_without_complete_observed_trace":size-full_trace_cases,
        "potentially_incomplete_event_window_count":sum(
            int(row["audit_event_window_limited"]) for row in rows),
        "case_preview":rows[:12],
        "case_preview_limit":12,
        "case_preview_is_sample":size>12,
        "worksheet_full_cohort_available":True,
        "worksheet_status":"AWAITING_HUMAN_REVIEW",
        "stage_count_basis":"DISTINCT_AUTHORIZED_CASES_WITH_AUDIT_EVIDENCE_OBSERVED_IN_SELECTED_UTC_PERIOD",
        "stage_counts_are_not_lifetime_history":True,
        "complete_trace_is_not_formal_acceptance":True,
        "automated_pilot_acceptance_granted":False,
        "authorized_human_signoff_received":False,
        "source_authenticity_verified":False,
        "legal_verdict_confirmed":False,
        "jurisdiction_approval_confirmed":False,
        "no_new_sql_queries":True,
        "no_casework_writes":True,
        "paid_model_calls":0,
        "next_steps":[
            "SELECT_AUTHORIZED_REAL_CASES",
            "OFFICER_CONFIRM_SOURCE_REVIEW",
            "RECEIVING_OFFICER_VALIDATE_CASEWORK",
            "INDEPENDENT_REVIEWER_CONFIRM_LATEST_REPORT",
            "CAPTURE_SEPARATE_SIGNOFF"
        ] if size else [
            "WAIT_FOR_AUTHORIZED_REAL_CASES",
            "DO_NOT_PRESENT_SYNTHETIC_QA_AS_HUMAN_ACCEPTANCE"
        ],
    }
