"""v157.7 period audit CSV status matches management approval reconciliation."""
from datetime import datetime,timedelta
import csv,io
from app.models import User
from app.access import profile
from app.casework import CaseReport,CaseTransition
from app.management_reporting import build_briefing,briefing_activity_csv
from test_management_briefings_v1468 import dataset

def event(cid):
    return CaseTransition(case_id=cid,actor_id=1,action="REPORT_APPROVED",
                          happened_at=datetime.utcnow()-timedelta(seconds=5))

def csv_rows(db,uid=1):
    resp=briefing_activity_csv("weekly","",db.get(User,uid),db)
    return list(csv.DictReader(io.StringIO(resp.body.decode("utf-8-sig"))))

def test_approved_case_is_marked_currently_approved_in_csv():
    db=dataset()
    try:
        db.add(event(1));db.commit()
        rows=csv_rows(db)
        row=next(r for r in rows if r["Case ID"]=="1")
        assert row["Latest report status at export (approval activity only)"]=="APPROVED"
        assert row["Current approval reconciliation"]=="STILL_APPROVED"
        summary=build_briefing(db,profile(db,db.get(User,1)),1)["period_audit_activity"]
        assert summary["approval_activity_reconciliation_totals_match"]
        assert summary["approval_activity_cases_latest_approved"]==1
    finally:db.close()

def test_superseded_approval_has_current_draft_status_and_no_current_approval():
    db=dataset()
    try:
        now=datetime.utcnow()
        db.add(event(1))
        db.add(CaseReport(id=9,case_id=1,title="Revision draft",
            status="DRAFT",created_by=1,
            created_at=now+timedelta(seconds=1),updated_at=now))
        db.commit()
        row=next(r for r in csv_rows(db) if r["Case ID"]=="1")
        assert row["Latest report status at export (approval activity only)"]=="DRAFT"
        assert row["Current approval reconciliation"]=="SUPERSEDED_OR_NOT_APPROVED"
        summary=build_briefing(db,profile(db,db.get(User,1)),1)["period_audit_activity"]
        assert summary["approval_activity_reconciliation_totals_match"]
        assert summary["approval_activity_cases_latest_not_approved"]==1
    finally:db.close()

def test_missing_saved_report_is_explicit_in_csv_and_summary():
    db=dataset()
    try:
        db.add(event(2));db.commit()
        row=next(r for r in csv_rows(db) if r["Case ID"]=="2")
        assert row["Latest report status at export (approval activity only)"]=="NO_REPORT"
        assert row["Current approval reconciliation"]=="NO_SAVED_REPORT"
        summary=build_briefing(db,profile(db,db.get(User,1)),1)["period_audit_activity"]
        assert summary["approval_activity_cases_without_saved_report"]==1
        assert summary["approval_activity_reconciliation_totals_match"]
    finally:db.close()

def test_non_approval_event_does_not_claim_latest_status_was_checked():
    db=dataset()
    try:
        db.add(CaseTransition(case_id=1,actor_id=1,action="REPORT_SUBMITTED",
            happened_at=datetime.utcnow()-timedelta(seconds=5)))
        db.commit()
        row=next(r for r in csv_rows(db) if r["Case ID"]=="1")
        assert row["Latest report status at export (approval activity only)"]=="NOT_CHECKED_NO_APPROVAL_EVENT"
        assert row["Current approval reconciliation"]=="NOT_APPLICABLE_NO_APPROVAL_EVENT"
    finally:db.close()

def test_province_csv_scope_excludes_bali_approval():
    db=dataset()
    try:
        db.add(event(1));db.add(event(3));db.commit()
        rows=csv_rows(db,2)
        assert {r["Case ID"] for r in rows}=={"1"}
        assert rows[0]["Current approval reconciliation"]=="STILL_APPROVED"
        summary=build_briefing(db,profile(db,db.get(User,2)),2)["period_audit_activity"]
        assert summary["distinct_cases_with_approval"]==1
        assert summary["approval_activity_reconciliation_totals_match"]
    finally:db.close()
