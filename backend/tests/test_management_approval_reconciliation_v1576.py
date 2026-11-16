"""v157.6 reconcile period approval events with latest saved report status."""
from datetime import datetime,timedelta
from app.models import User
from app.access import profile
from app.casework import CaseReport,CaseTransition
from app.management_reporting import build_briefing
from test_management_briefings_v1468 import dataset

def approval(cid,time):
    return CaseTransition(case_id=cid,actor_id=1,
        action="REPORT_APPROVED",happened_at=time)

def snapshot(db,uid=1):
    return build_briefing(db,profile(db,db.get(User,uid)),uid,language="en")

def test_currently_approved_report_reconciles_with_approval_activity():
    db=dataset()
    try:
        db.add(approval(1,datetime.utcnow()-timedelta(seconds=5)))
        db.commit()
        a=snapshot(db)["period_audit_activity"]
        assert a["distinct_cases_with_approval"]==1
        assert a["approval_activity_cases_latest_approved"]==1
        assert a["approval_activity_cases_latest_not_approved"]==0
        assert a["approval_activity_cases_without_saved_report"]==0
        assert a["approval_activity_latest_status_reconciled"]
    finally:db.close()

def test_new_draft_supersedes_approval_event_without_inflating_current_approved():
    db=dataset()
    try:
        now=datetime.utcnow()
        db.add(approval(1,now-timedelta(seconds=5)))
        db.add(CaseReport(id=9,case_id=1,title="Revised draft",
             status="DRAFT",created_by=1,created_at=now+timedelta(seconds=1),
             updated_at=now+timedelta(seconds=1)))
        db.commit()
        report=snapshot(db)
        a=report["period_audit_activity"]
        assert a["report_approved_events"]==1
        assert a["approval_activity_cases_latest_approved"]==0
        assert a["approval_activity_cases_latest_not_approved"]==1
        assert a["approval_activity_cases_without_saved_report"]==0
        assert report["metrics"]["approved_reports"]==0
        assert any(x["label"]=="Approval-activity cases no longer approved"
                   and x["value"]==1 for x in report["template"]["scorecard"])
    finally:db.close()

def test_orphaned_approval_audit_is_explicit_not_silently_approved():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        db.add_all([approval(1,now),approval(2,now),approval(2,now)])
        db.commit()
        a=snapshot(db)["period_audit_activity"]
        assert a["report_approved_events"]==3
        assert a["distinct_cases_with_approval"]==2
        assert a["approval_activity_cases_latest_approved"]==1
        assert a["approval_activity_cases_latest_not_approved"]==0
        assert a["approval_activity_cases_without_saved_report"]==1
    finally:db.close()

def test_provincial_visibility_prevents_cross_province_approval_reconciliation():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        db.add_all([approval(1,now),approval(3,now)])
        db.add(CaseReport(id=9,case_id=3,title="Bali approved",status="APPROVED",
                          created_by=1,created_at=now,updated_at=now))
        db.commit()
        a=snapshot(db,2)["period_audit_activity"]
        assert a["distinct_cases_with_approval"]==1
        assert a["approval_activity_cases_latest_approved"]==1
        assert a["approval_activity_cases_latest_not_approved"]==0
        assert a["approval_activity_cases_without_saved_report"]==0
    finally:db.close()
