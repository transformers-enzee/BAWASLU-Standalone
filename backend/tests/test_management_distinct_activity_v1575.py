"""v157.5 distinct affected cases versus audit-event volume."""
from datetime import datetime,timedelta
import csv,io
from app.models import User
from app.access import profile
from app.casework import CaseAssignment,CaseTransition
from app.management_reporting import build_briefing,briefing_activity_csv
from test_management_briefings_v1468 import dataset

def event(cid,action,time):
    return CaseTransition(case_id=cid,actor_id=1,action=action,happened_at=time)

def test_repeated_events_count_once_per_distinct_case():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        db.add_all([
            event(1,"REPORT_SUBMITTED",now),event(1,"REPORT_SUBMITTED",now),
            event(1,"REPORT_RETURNED",now),event(1,"REPORT_RETURNED",now),
            event(1,"REPORT_APPROVED",now),event(1,"REPORT_APPROVED",now),
            event(1,"REPORT_REVISION_DRAFTED",now),event(1,"REPORT_REVISION_DRAFTED",now),
            event(2,"REPORT_APPROVED",now)])
        db.commit()
        report=build_briefing(db,profile(db,db.get(User,1)),1,
                              now=now+timedelta(minutes=1),language="en")
        a=report["period_audit_activity"]
        assert a["report_submitted_events"]==2
        assert a["distinct_cases_with_submission"]==1
        assert a["report_returned_events"]==2
        assert a["distinct_cases_with_return"]==1
        assert a["report_approved_events"]==3
        assert a["distinct_cases_with_approval"]==2
        assert a["revision_drafted_events"]==2
        assert a["distinct_cases_with_revision"]==1
        assert a["authorized_cases_with_observed_activity"]==2
        assert a["distinct_counts_do_not_prove_latest_report_status"]
        assert any(row["label"]=="Distinct cases with approval activity" and row["value"]==2
          for row in report["template"]["scorecard"])
    finally:db.close()

def test_older_case_multiple_approvals_one_distinct_older_case():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        old=db.get(CaseAssignment,4)
        old.created_at=now-timedelta(days=40)
        db.add_all([event(4,"REPORT_APPROVED",now),event(4,"REPORT_APPROVED",now)])
        db.commit()
        report=build_briefing(db,profile(db,db.get(User,1)),1,
                              now=now+timedelta(minutes=1),language="en")
        a=report["period_audit_activity"]
        assert a["approved_events_on_older_cases"]==2
        assert a["distinct_older_cases_with_approval"]==1
    finally:db.close()

def test_csv_one_row_per_case_with_distinct_indicators():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        db.add_all([event(1,"REPORT_APPROVED",now),
                    event(1,"REPORT_APPROVED",now),
                    event(1,"REPORT_RETURNED",now),
                    event(2,"REPORT_REVISION_DRAFTED",now)])
        db.commit()
        result=briefing_activity_csv("weekly","",db.get(User,1),db)
        rows=list(csv.DictReader(io.StringIO(result.body.decode("utf-8-sig"))))
        a=next(x for x in rows if x["Case ID"]=="1")
        b=next(x for x in rows if x["Case ID"]=="2")
        assert sum(x["Case ID"]=="1" for x in rows)==1
        assert a["Report approved audit events"]=="2"
        assert a["Distinct approved case indicator"]=="YES"
        assert a["Distinct returned case indicator"]=="YES"
        assert b["Distinct revised case indicator"]=="YES"
    finally:db.close()

def test_province_scope_does_not_leak_outside_case_activity():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        db.add_all([event(3,"REPORT_APPROVED",now),event(1,"REPORT_APPROVED",now)])
        db.commit()
        report=build_briefing(db,profile(db,db.get(User,2)),2,
                              now=now+timedelta(minutes=1),language="en")
        assert report["period_audit_activity"]["distinct_cases_with_approval"]==1
    finally:db.close()
