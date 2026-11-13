"""Bounded read-only officer casework progress for already-authorized findings.

Uses SQL window functions to fetch the latest report per case and last 200
audit events per case in two queries. Never reads other jurisdictions' cases,
reveals audit notes, changes permissions, or certifies legal/source truth.
"""
from collections import defaultdict
from sqlalchemy import func
from .casework import CaseReport, CaseTransition, _acceptance_trace

_STEP_KEYS={
    "source_linked","receiving_officer_accepted","original_source_checked",
    "latest_report_submitted","independent_report_approval",
}

def summarize_authorized_case_progress(db,cases):
    selected=list(dict((int(case.id),case) for case in cases).values())[:8]
    if not selected:
        return {}
    ids=[case.id for case in selected]
    ranked_events=db.query(
        CaseTransition.id.label("event_id"),
        func.row_number().over(
            partition_by=CaseTransition.case_id,
            order_by=CaseTransition.id.desc()).label("event_rank")
    ).filter(CaseTransition.case_id.in_(ids)).subquery()
    event_rows=db.query(CaseTransition).join(
        ranked_events,CaseTransition.id==ranked_events.c.event_id).filter(
            ranked_events.c.event_rank<=200).order_by(
                CaseTransition.case_id,CaseTransition.id).all()
    ranked_reports=db.query(
        CaseReport.id.label("report_id"),
        func.row_number().over(
            partition_by=CaseReport.case_id,
            order_by=(CaseReport.created_at.desc(),CaseReport.id.desc())
        ).label("report_rank")
    ).filter(CaseReport.case_id.in_(ids)).subquery()
    latest_reports=db.query(CaseReport).join(
        ranked_reports,CaseReport.id==ranked_reports.c.report_id
    ).filter(ranked_reports.c.report_rank==1).all()
    grouped_events=defaultdict(list)
    for event in event_rows:
        grouped_events[event.case_id].append(event)
    reports={report.case_id:report for report in latest_reports}
    output={}
    for case in selected:
        report=reports.get(case.id)
        audit=_acceptance_trace(
            case,grouped_events[case.id],[report] if report else [])
        steps=[{"key":x["key"],"done":bool(x["done"])}
               for x in audit["steps"] if x["key"] in _STEP_KEYS]
        incomplete=next((step["key"] for step in steps if not step["done"]),None)
        source_review=audit.get("latest_source_review_status")
        output[case.id]={
            "schema":"BAWASLU_CASEWORK_AUDIT_PROGRESS_V1534",
            "case_id":case.id,
            "case_status":case.status,
            "latest_report_status":report.status if report else "NO_REPORT",
            "steps":steps,
            "completed_steps":sum(x["done"] for x in steps),
            "total_steps":5,
            "next_uncompleted_step":incomplete,
            "latest_source_review_status":source_review if source_review in {
                "SOURCE_CHECKED","SOURCE_UNAVAILABLE","NEEDS_INFORMATION"} else "NOT_RECORDED_OR_UNKNOWN",
            "audit_event_limit_reached":bool(audit["event_window_limited"]),
            "event_history_may_be_incomplete":bool(audit["event_window_limited"]),
            "latest_report_version_only":True,
            "casework_progress_is_legal_verdict":False,
            "source_truth_verified":False,
            "human_acceptance_certified":False,
            "no_casework_action_created":True,
        }
    return output
