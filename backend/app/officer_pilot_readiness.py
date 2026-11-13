"""Authorized officer-pilot acceptance evidence, without granting acceptance.

This is an observational checklist from existing casework events in the chosen
UTC reporting window. The counts show distinct authorized cases with each
audit stage, never the number of actions or a claim of formal client sign-off.
No live writes, no additional SQL queries, no inference, and no raw audit notes.
"""
from collections import defaultdict
from .casework import _acceptance_trace

_STAGES=("source_linked","receiving_officer_accepted","original_source_checked",
         "latest_report_submitted","independent_report_approval")

def officer_pilot_readiness(cases,latest_by_case,transitions):
    selected_events=defaultdict(list)
    for item in sorted(transitions,key=lambda event:event.id):
        selected_events[item.case_id].append(item)
    counts={key:0 for key in _STAGES}
    full_trace_cases=0
    truncated_or_incomplete_history=0
    for case in cases:
        report=latest_by_case.get(case.id)
        events=selected_events[case.id]
        # All staged events are observed only inside selected UTC window;
        # source events outside this window must not be inferred missing.
        trace=_acceptance_trace(case,events,[report] if report else [])
        observed={item["key"]:bool(item["done"]) for item in trace["steps"]}
        for step in _STAGES:
            counts[step]+=int(observed.get(step,False))
        full_trace_cases+=int(all(observed.get(step,False) for step in _STAGES))
        truncated_or_incomplete_history+=int(bool(trace["event_window_limited"]))
    size=len(cases)
    return {
        "schema":"BAWASLU_OFFICER_PILOT_EVIDENCE_V1540",
        "authorized_case_count":size,
        "real_casework_available_in_scope":bool(size),
        "stage_counts":counts,
        "five_stage_observed_case_count":full_trace_cases,
        "cases_without_complete_observed_trace":size-full_trace_cases,
        "potentially_incomplete_event_window_count":truncated_or_incomplete_history,
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
