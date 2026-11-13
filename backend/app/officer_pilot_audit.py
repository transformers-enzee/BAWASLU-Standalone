"""Read-only, bounded evidence view for already-authorized officer pilot cases.

Do not call this with unscoped case assignments. Existing case permissions and
fresh source eligibility must be verified by the calling endpoint first.
"""
from collections import defaultdict
from sqlalchemy import func
from .casework import CaseTransition, CaseReport, _acceptance_trace
from .officer_pilot_readiness import _STAGES

def observed_casework_stages(db,cases):
    visible={int(case.id):case for case in cases}
    if not visible:
        return {}
    case_ids=sorted(visible)
    # Bound results per case, not for the whole pilot cohort, so a noisy
    # history for one case cannot hide the trace of another case.
    transitions_ranked=(db.query(
        CaseTransition.id.label("audit_id"),
        func.row_number().over(
            partition_by=CaseTransition.case_id,
            order_by=CaseTransition.id.desc()).label("row_num"))
        .filter(CaseTransition.case_id.in_(case_ids)).subquery())
    events=(db.query(CaseTransition)
        .join(transitions_ranked,CaseTransition.id==transitions_ranked.c.audit_id)
        .filter(transitions_ranked.c.row_num<=200)
        .order_by(CaseTransition.case_id,CaseTransition.id).all())
    reports_ranked=(db.query(
        CaseReport.id.label("report_id"),
        func.row_number().over(
            partition_by=CaseReport.case_id,
            order_by=CaseReport.id.desc()).label("row_num"))
        .filter(CaseReport.case_id.in_(case_ids)).subquery())
    reports=(db.query(CaseReport)
        .join(reports_ranked,CaseReport.id==reports_ranked.c.report_id)
        .filter(reports_ranked.c.row_num==1).all())
    grouped=defaultdict(list)
    for event in events:
        grouped[event.case_id].append(event)
    latest={report.case_id:report for report in reports}
    output={}
    for case_id,case in visible.items():
        report=latest.get(case_id)
        trace=_acceptance_trace(case,grouped[case_id],[report] if report else [])
        output[case_id]={
            "observed_stages":{s["key"]:bool(s["done"]) for s in trace["steps"]
                               if s["key"] in _STAGES},
            "audit_event_window_limited":bool(trace["event_window_limited"]),
            "source_authenticity_verified":False,
            "legal_approval_granted":False,
            "human_pilot_signoff_received":False,
        }
    return output
