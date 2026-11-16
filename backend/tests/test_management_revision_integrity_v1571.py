"""v157.1 casework reporting latest-version integrity; in-memory SQLite only."""
from datetime import datetime,timedelta
from app.access import profile
from app.models import User
from app.casework import CaseReport
from app.management_reporting import build_briefing
from test_management_briefings_v1468 import dataset

def briefing(db,uid=1):
    return build_briefing(db,profile(db,db.get(User,uid)),uid,language="en")

def add(db,id,case_id,status,offset):
    return CaseReport(id=id,case_id=case_id,title="UAT report version",
      status=status,created_by=1,created_at=datetime.utcnow()+timedelta(seconds=offset),
      updated_at=datetime.utcnow())

def test_prior_returned_version_retained_without_counting_as_current():
    db=dataset()
    try:
        db.add(add(db,9,1,"RETURNED",1))
        db.add(add(db,10,1,"APPROVED",2))
        db.commit()
        r=briefing(db)
        v=r["report_version_integrity"]
        assert r["metrics"]["assignments"]==3
        assert r["metrics"]["approved_reports"]==1
        assert r["metrics"]["submitted_reports"]==0
        assert r["metrics"]["report_versions_recorded"]==3
        assert r["report_status_counts"]=={"APPROVED":1}
        assert v["total_stored_versions"]==3
        assert v["superseded_versions"]==2
        assert v["superseded_returned_versions"]==1
        assert v["superseded_approved_versions"]==1
        assert v["latest_approved_after_return"]==1
        assert v["cases_with_multiple_versions"]==1
        assert v["latest_returned_awaiting_revision"]==0
    finally: db.close()

def test_latest_draft_after_return_is_not_approved_or_submitted():
    db=dataset()
    try:
        db.add(add(db,9,1,"RETURNED",1))
        db.add(add(db,10,1,"DRAFT",2))
        db.commit()
        r=briefing(db)
        v=r["report_version_integrity"]
        assert r["metrics"]["approved_reports"]==0
        assert r["metrics"]["submitted_reports"]==0
        assert r["report_status_counts"]=={"DRAFT":1}
        assert v["latest_draft_after_return"]==1
        assert v["latest_approved_after_return"]==0
        assert v["latest_returned_awaiting_revision"]==0
    finally:db.close()

def test_latest_returned_requires_revision_despite_older_approved_version():
    db=dataset()
    try:
        db.add(add(db,9,1,"RETURNED",1))
        db.commit()
        r=briefing(db)
        v=r["report_version_integrity"]
        assert r["metrics"]["approved_reports"]==0
        assert r["report_status_counts"]=={"RETURNED":1}
        assert v["latest_returned_awaiting_revision"]==1
        assert v["superseded_approved_versions"]==1
        assert v["superseded_returned_versions"]==0
    finally: db.close()

def test_reporting_history_remains_jurisdiction_scoped():
    db=dataset()
    try:
        db.add(add(db,9,1,"RETURNED",1))
        db.add(add(db,10,1,"APPROVED",2))
        db.add(add(db,11,3,"RETURNED",3))
        db.commit()
        r=briefing(db,2) # Riau province: excludes Bali case 3
        v=r["report_version_integrity"]
        assert v["authorized_cases"]==2
        assert v["case_count_with_report"]==1
        assert v["total_stored_versions"]==3
        assert v["superseded_returned_versions"]==1
        assert v["latest_returned_awaiting_revision"]==0
        assert r["metrics"]["approved_reports"]==1
    finally:db.close()

def test_report_revision_integrity_empty_scope_is_explicit():
    db=dataset()
    try:
        r=briefing(db,3)
        v=r["report_version_integrity"]
        assert v["authorized_cases"]==1
        assert v["case_count_with_report"]==0
        assert v["total_stored_versions"]==0
        assert v["historical_versions_are_not_approvals"] is True
    finally:db.close()
