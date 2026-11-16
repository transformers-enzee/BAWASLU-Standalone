"""v157.4: independent event-date reporting with jurisdiction and old cases."""
from datetime import datetime,timedelta
import io,csv
from app.models import User
from app.access import profile
from app.casework import CaseAssignment,CaseTransition
from app.management_reporting import build_briefing,briefing_activity_csv
from test_management_briefings_v1468 import dataset

def test_old_case_approval_event_is_visible_as_activity_not_new_assignment():
    db=dataset()
    try:
        current=datetime.utcnow()
        old=db.get(CaseAssignment,4)
        old.created_at=current-timedelta(days=40)
        db.add(CaseTransition(case_id=4,actor_id=1,action="REPORT_APPROVED",
          happened_at=current-timedelta(hours=2)))
        db.add(CaseTransition(case_id=4,actor_id=1,action="REPORT_RETURNED",
          happened_at=current-timedelta(days=22)))
        db.commit()
        report=build_briefing(db,profile(db,db.get(User,1)),1,
           now=current,language="en")
        activity=report["period_audit_activity"]
        assert report["metrics"]["assignments"]==3
        assert activity["older_cases_with_observed_activity"]==1
        assert activity["approved_events_on_older_cases"]==1
        assert activity["report_approved_events"]==1
        assert activity["report_returned_events"]==0
        assert report["template"]["period_audit_activity"]["older_cases_with_observed_activity"]==1
        assert any(row["label"]=="Approval audit events on older cases" and row["value"]==1
            for row in report["template"]["scorecard"])
    finally:db.close()

def test_province_scope_prevents_old_case_activity_leak():
    db=dataset()
    try:
        old=db.get(CaseAssignment,4)
        db.add(CaseTransition(case_id=4,actor_id=1,action="REPORT_APPROVED",
          happened_at=datetime.utcnow()))
        db.commit()
        r=build_briefing(db,profile(db,db.get(User,2)),2,language="en")
        assert r["period_audit_activity"]["approved_events_on_older_cases"]==0
        assert r["period_audit_activity"]["older_cases_with_observed_activity"]==0
    finally:db.close()

def test_distinct_case_count_does_not_confuse_multiple_events():
    db=dataset()
    try:
        now=datetime.utcnow()
        db.add(CaseTransition(case_id=1,actor_id=1,action="REPORT_SUBMITTED",
          happened_at=now))
        db.add(CaseTransition(case_id=1,actor_id=1,action="REPORT_RETURNED",
          happened_at=now))
        db.add(CaseTransition(case_id=1,actor_id=1,action="REPORT_SUBMITTED",
          happened_at=now))
        db.commit()
        r=build_briefing(db,profile(db,db.get(User,1)),1,language="en")
        a=r["period_audit_activity"]
        assert a["report_submitted_events"]==2
        assert a["report_returned_events"]==1
        assert a["authorized_cases_with_observed_activity"]>=1
        assert a["event_counts_are_not_distinct_reports"]
    finally:db.close()

def test_activity_csv_contains_older_cases_without_changing_main_csv_cohort():
    db=dataset()
    try:
        old=db.get(CaseAssignment,4)
        db.add(CaseTransition(case_id=4,actor_id=1,action="REPORT_APPROVED",
          happened_at=datetime.utcnow()))
        db.commit()
        response=briefing_activity_csv("weekly","",db.get(User,1),db)
        rows=list(csv.DictReader(io.StringIO(response.body.decode("utf-8-sig"))))
        case=next(x for x in rows if x["Case ID"]=="4")
        assert case["Created in selected window"]=="NO"
        assert case["Report approved audit events"]=="1"
        assert response.headers["Cache-Control"]=="private, no-store"
    finally:db.close()
