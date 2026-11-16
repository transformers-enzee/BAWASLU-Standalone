"""v157.9: management reads avoid full case report payloads and batch large cohorts."""
from datetime import datetime,timedelta
from sqlalchemy import event
from app.models import User
from app.access import profile
from app.casework import CaseAssignment,CaseReport,CaseTransition
from app.management_reporting import build_briefing,_scoped_casework_window
from test_management_briefings_v1468 import dataset

def test_report_status_metrics_survive_lightweight_metadata_projection():
    db=dataset()
    try:
        now=datetime.utcnow()
        db.add(CaseReport(id=9,case_id=1,title="Returned historical report",
            status="RETURNED",created_by=1,created_at=now+timedelta(seconds=1),
            executive_summary="PRIVATE REPORT BODY SHOULD NOT BE FETCHED"))
        db.add(CaseReport(id=10,case_id=1,title="Latest approved report",
            status="APPROVED",created_by=1,created_at=now+timedelta(seconds=2),
            findings="PRIVATE REPORT FINDINGS SHOULD NOT BE FETCHED"))
        db.commit()
        report=build_briefing(db,profile(db,db.get(User,1)),1,language="en")
        assert report["metrics"]["approved_reports"]==1
        assert report["metrics"]["report_versions_recorded"]==3
        assert report["report_version_integrity"]["superseded_returned_versions"]==1
        assert report["report_version_integrity"]["latest_approved_after_return"]==1
    finally:db.close()

def test_management_report_sql_excludes_large_body_columns_and_reviewer_identity():
    db=dataset()
    captured=[]
    def capture(conn,cursor,statement,parameters,context,executemany):
        captured.append(statement.lower())
    event.listen(db.bind,"before_cursor_execute",capture)
    try:
        build_briefing(db,profile(db,db.get(User,1)),1)
        projection=[s for s in captured if
            "from case_reports" in s and "case_reports.case_id in" in s]
        assert projection
        for sql in projection:
            select=sql.split(" from case_reports",1)[0]
            for column in ("executive_summary","verification_notes","recommendations",
                           "findings","source_snapshot_json","review_comment","reviewed_by"):
                assert column not in select,column
        transitions=[s for s in captured if
            "from case_transitions" in s and "case_transitions.case_id in" in s]
        assert transitions
        for sql in transitions:
            select=sql.split(" from case_transitions",1)[0]
            assert "actor_id" not in select
    finally:
        event.remove(db.bind,"before_cursor_execute",capture)
        db.close()

def test_source_review_audit_details_remain_available_without_entire_event():
    db=dataset()
    try:
        import json
        now=datetime.utcnow()
        db.add(CaseTransition(case_id=1,actor_id=1,
            action="SOURCE_REVIEW_RECORDED",happened_at=now,
            details_json=json.dumps({"status":"SOURCE_CHECKED",
               "original_source_opened":True,"source_type":"SOCIAL",
               "source_id":"15","source_url":"https://example.invalid/post/15"})))
        db.commit()
        report=build_briefing(db,profile(db,db.get(User,1)),1)
        assert report["casework_progress"]["source_check_attested_in_window"]==1
    finally:db.close()

def test_batched_report_and_transition_queries_handle_over_400_cases():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(minutes=1)
        common=dict(source_type="SOCIAL",source_url="https://example.invalid/post",
            originating_scope="NATIONAL",target_scope="NATIONAL",
            target_department="Penanganan Pelanggaran",created_by=1)
        for cid in range(1000,1403):
            db.add(CaseAssignment(id=cid,title="Batch case",source_id=str(cid),
                status="IN_REVIEW",created_at=now,**common))
            db.add(CaseReport(case_id=cid,title="Batch draft",status="DRAFT",
                created_by=1,created_at=now))
            db.add(CaseTransition(case_id=cid,actor_id=1,action="ASSIGNED",
                happened_at=now))
        db.commit()
        access=profile(db,db.get(User,1))
        cases,_,_,_,reports,transitions,latest=_scoped_casework_window(
            db,access,1,"weekly")
        assert len(cases)==406
        assert len(reports)==404
        assert len(transitions)==404
        assert len(latest)==404
        report=build_briefing(db,access,1)
        assert report["metrics"]["assignments"]==406
        assert report["metrics"]["report_versions_recorded"]==404
        assert report["metrics"]["approved_reports"]==1
    finally:db.close()

def test_province_role_cannot_see_unrelated_full_or_metadata_reports():
    db=dataset()
    try:
        report=build_briefing(db,profile(db,db.get(User,2)),2)
        assert report["metrics"]["assignments"]==2
        assert report["metrics"]["report_versions_recorded"]==1
        assert report["metrics"]["approved_reports"]==1
    finally:db.close()
