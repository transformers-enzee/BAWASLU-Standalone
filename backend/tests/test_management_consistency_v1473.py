"""v147.3 management reporting consistency and SQL-scope regressions.

No live database writes, no external API or paid model calls.
"""
from datetime import datetime, timedelta
from sqlalchemy import event
from app.access import profile
from app.models import User, AccessGrant
from app.casework import CaseAssignment, CaseReport
from app.management_reporting import build_briefing, scoped_cases
from test_management_briefings_v1468 import dataset


def _get(db, uid, **kwargs):
    user = db.get(User, uid)
    return build_briefing(db, profile(db, user), uid, language="en", **kwargs)


def test_historical_report_versions_never_inflate_current_kpis():
    db = dataset()
    try:
        db.add(CaseReport(id=9, case_id=1, title="Returned revision",
            status="RETURNED", created_by=1,
            created_at=datetime.utcnow() + timedelta(seconds=1),
            updated_at=datetime.utcnow()))
        db.commit()
        summary = _get(db, 2)
        assert summary["metrics"]["assignments"] == 2
        assert summary["metrics"]["report_versions_recorded"] == 2
        assert summary["metrics"]["assignments_with_reports"] == 1
        assert summary["metrics"]["assignments_without_reports"] == 1
        assert summary["metrics"]["approved_reports"] == 0
        assert summary["metrics"]["submitted_reports"] == 0
        assert summary["report_status_counts"] == {"RETURNED": 1}
        assert summary["report_status_basis"] == "LATEST_REPORT_PER_AUTHORIZED_ASSIGNMENT"
        assert summary["recent_cases"][0]["latest_report_status"] in (None, "RETURNED")
        status_for_case = {row["id"]: row["latest_report_status"] for row in summary["recent_cases"]}
        assert status_for_case[1] == "RETURNED"
        assert "0 have approved workflow status" in summary["template"]["executive_summary"]
        assert "latest report version" in " ".join(summary["template"]["methodology"]).lower()
        assert "Bali" not in str(summary["template"]["findings"])
    finally:
        db.close()


def test_database_query_applies_province_boundary_before_materializing_rows():
    db = dataset()
    statements = []
    try:
        def capture(conn, cursor, statement, parameters, context, executemany):
            if "FROM case_assignments" in statement:
                statements.append(statement)
        event.listen(db.bind, "before_cursor_execute", capture)
        try:
            rows, *_ = scoped_cases(db, profile(db, db.get(User, 2)), 2, "weekly")
        finally:
            event.remove(db.bind, "before_cursor_execute", capture)
        assert len(rows) == 2
        assert statements
        assert "originating_province" in statements[0]
        assert "target_province" in statements[0]
        assert "verified_province" in statements[0]
        assert " OR " in statements[0]
        assert all(row.target_province == "Riau" for row in rows)
    finally:
        db.close()


def test_provincial_user_with_no_province_has_no_casework_results():
    db = dataset()
    try:
        grant = db.query(AccessGrant).filter_by(user_id=2).one()
        grant.province = ""
        db.commit()
        summary = _get(db, 2)
        assert summary["metrics"]["assignments"] == 0
        assert summary["report_coverage"]["preview_rows"] == 0
        assert summary["template"]["source_appendix"] == []
    finally:
        db.close()


def test_full_metrics_separated_from_twelve_row_preview_and_eight_row_template():
    db = dataset()
    try:
        baseline = db.get(CaseAssignment, 1)
        now = datetime.utcnow()
        for i in range(5, 20):
            db.add(CaseAssignment(
                id=i, title=f"Additional Riau case {i}",
                source_type="SOCIAL", source_id=str(i), campaign_id=10,
                source_url="https://example.invalid/" + str(i),
                source_excerpt="Source evidence requires human verification",
                originating_scope="NATIONAL", originating_province="",
                target_scope="PROVINCE", target_province="Riau",
                verified_province="Riau", target_department=baseline.target_department,
                created_by=1, created_at=now, updated_at=now, status="OPEN"))
        db.commit()
        summary = _get(db, 2)
        coverage = summary["report_coverage"]
        assert summary["metrics"]["assignments"] == 17
        assert coverage["assignments_in_period"] == 17
        assert coverage["preview_limit"] == 12
        assert coverage["preview_rows"] == 12
        assert coverage["template_limit"] == 8
        assert coverage["template_rows"] == 8
        assert coverage["preview_is_sample"] is True
        assert coverage["template_is_sample"] is True
        assert len(summary["recent_cases"]) == 12
        assert len(summary["template"]["findings"]) == 8
        assert "17" in summary["template"]["coverage_note"]
        assert summary["counts_complete_for_window"] is True
        assert summary["query_scope"] == "SQL_AND_CASEWORK_VISIBILITY"
    finally:
        db.close()
