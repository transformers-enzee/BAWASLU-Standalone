"""v154.2 read-only officer review packet and role-scoped worksheet export.

All DB work uses isolated in-memory SQLite, never live Supabase.
"""
import csv
import io
from datetime import datetime,timedelta
from types import SimpleNamespace as Obj
from sqlalchemy import event
from fastapi import HTTPException
import pytest

from app.casework import (
    CaseAssignment,CaseReport,CaseTransition,ReportAction,
    acknowledge_case,create_report,record_source_review,transition_report)
from app.management_reporting import officer_pilot_csv,build_briefing
from app.officer_pilot_readiness import officer_pilot_case_rows,officer_pilot_readiness
from app.access import profile
from app.models import User
from test_management_briefings_v1468 import dataset as management_dataset
from test_casework_workflow import dataset as officer_dataset
from test_officer_acceptance_v1480 import _case,_user,_review,_report

STAGES=("source_linked","receiving_officer_accepted","original_source_checked",
        "latest_report_submitted","independent_report_approval")

def export(db,uid=1,period="weekly",topic=""):
    return officer_pilot_csv(period,topic,db.get(User,uid),db)

def rows(response):
    return list(csv.DictReader(io.StringIO(response.body.decode("utf-8-sig"))))

def test_empty_scope_downloads_header_only_not_an_approved_sheet():
    db=management_dataset()
    try:
        response=export(db,3,topic="Riau")
        assert response.status_code==200
        assert rows(response)==[]
        assert response.headers["x-pilot-case-count"]=="0"
        assert response.headers["x-pilot-approval"]=="AWAITING_HUMAN_REVIEW"
        assert "Officer assessment (human entry)" in response.body.decode("utf-8-sig")
        assert response.headers["cache-control"]=="private, no-store"
    finally:db.close()

def test_national_officer_receives_three_authorized_cases_and_old_one_is_excluded():
    db=management_dataset()
    try:
        result=rows(export(db,1))
        assert {x["Case ID"] for x in result}=={"1","2","3"}
        assert "4" not in {x["Case ID"] for x in result}
        assert all(x["Acceptance decision (human entry)"]=="" for x in result)
    finally:db.close()

def test_riau_officer_cannot_export_bali_case_details():
    db=management_dataset()
    try:
        out=export(db,2)
        assert {r["Case ID"] for r in rows(out)}=={"1","2"}
        assert "Bali issue" not in out.body.decode("utf-8-sig")
        assert out.headers["x-pilot-case-count"]=="2"
    finally:db.close()

def test_bali_officer_cannot_export_riau_cases():
    db=management_dataset()
    try:
        assert {r["Case ID"] for r in rows(export(db,3))}=={"3"}
    finally:db.close()

def test_province_topic_filter_matches_management_report():
    db=management_dataset()
    try:
        response=export(db,2,topic="Riau")
        summary=build_briefing(db,profile(db,db.get(User,2)),2,topic="Riau")
        assert len(rows(response))==summary["officer_pilot_readiness"]["authorized_case_count"]
        assert len(rows(response))==2
        assert rows(export(db,2,topic="Bali"))==[]
    finally:db.close()

def test_both_exports_use_same_window_and_latest_report_status():
    db=management_dataset()
    try:
        result=rows(export(db,2))
        case1=next(row for row in result if row["Case ID"]=="1")
        assert case1["Latest report status"]=="APPROVED"
        assert case1["Independent reviewer approved (window audit)"]=="NOT_OBSERVED_IN_WINDOW"
        assert case1["Next audit check"]=="source_linked"
        assert "Source linked (window audit)" in case1
    finally:db.close()

def test_initial_source_linkage_is_distinct_from_officer_acceptance():
    db=officer_dataset()
    try:
        case=_case(db)
        one=rows(export(db,1))[0]
        assert one["Case ID"]==str(case["id"])
        assert one["Source linked (window audit)"]=="OBSERVED_IN_WINDOW"
        assert one["Receiving officer accepted (window audit)"]=="NOT_OBSERVED_IN_WINDOW"
        assert one["Observed stages (of 5)"]=="1"
        assert one["Next audit check"]=="receiving_officer_accepted"
    finally:db.close()

def test_recorded_receiving_acceptance_and_source_review_progress_to_three():
    db=officer_dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        one=rows(export(db,1))[0]
        assert one["Observed stages (of 5)"]=="3"
        assert one["Original source reviewed (window audit)"]=="OBSERVED_IN_WINDOW"
        assert one["Latest report submitted (window audit)"]=="NOT_OBSERVED_IN_WINDOW"
        assert one["Next audit check"]=="latest_report_submitted"
    finally:db.close()

def test_later_negative_source_correction_revokes_observed_check():
    db=officer_dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        record_source_review(case["id"],_review(
           status="NEEDS_INFORMATION",opened=False,
           note="Review must confirm source attribution before approval."),_user(db,2),db)
        one=rows(export(db,1))[0]
        assert one["Original source reviewed (window audit)"]=="NOT_OBSERVED_IN_WINDOW"
        assert one["Next audit check"]=="original_source_checked"
    finally:db.close()

def test_full_real_workflow_events_still_leave_human_signoff_columns_blank():
    db=officer_dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        report=create_report(case["id"],_report(),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="APPROVED"),_user(db,1),db)
        one=rows(export(db,1))[0]
        assert one["Observed stages (of 5)"]=="5"
        assert one["Next audit check"]==""
        for key in ("Officer assessment (human entry)",
                    "Officer reviewer (human entry)",
                    "Independent reviewer (human entry)",
                    "Acceptance decision (human entry)",
                    "Acceptance date UTC (human entry)",
                    "Review notes (human entry)"):
            assert one[key]==""
        result=officer_pilot_readiness([db.get(CaseAssignment,case["id"])],
                       {case["id"]:db.get(CaseReport,report["id"])},
                       db.query(CaseTransition).all())
        assert result["authorized_human_signoff_received"] is False
    finally:db.close()

def test_report_status_only_never_fakes_submission_or_independent_approval():
    db=management_dataset()
    try:
        one=next(row for row in rows(export(db,2)) if row["Case ID"]=="1")
        assert one["Latest report status"]=="APPROVED"
        assert one["Latest report submitted (window audit)"]=="NOT_OBSERVED_IN_WINDOW"
        assert one["Independent reviewer approved (window audit)"]=="NOT_OBSERVED_IN_WINDOW"
    finally:db.close()

def test_source_text_title_urls_and_audit_notes_not_exposed_in_packet():
    db=management_dataset()
    try:
        case=db.get(CaseAssignment,1)
        case.title="PRIVATE_CASE_TITLE"
        case.source_excerpt="PRIVATE_FULL_EVIDENCE"
        case.source_url="https://private.example.invalid/source"
        db.commit()
        content=export(db,2).body.decode("utf-8-sig")
        assert "PRIVATE_CASE_TITLE" not in content
        assert "PRIVATE_FULL_EVIDENCE" not in content
        assert "private.example.invalid" not in content
        # Column headers intentionally say "Officer assessment"; verify
        # actual fixture identities, not the header vocabulary, are absent.
        assert "Officer 1" not in content
        assert "Officer 2" not in content
    finally:db.close()

def test_csv_formula_injection_prefixes_untrusted_case_status():
    db=management_dataset()
    try:
        case=db.get(CaseAssignment,1)
        case.status='=HYPERLINK("https://evil.invalid","click")'
        db.commit()
        one=next(row for row in rows(export(db,2)) if row["Case ID"]=="1")
        assert one["Current case status"].startswith("'=HYPERLINK")
        assert not one["Current case status"].startswith("=")
    finally:db.close()

def test_worksheet_link_contains_only_safe_numeric_case_id():
    db=management_dataset()
    try:
        for row in rows(export(db,2)):
            assert row["Inbox casework link (permission rechecked)"]==(
                "/inbox?casework=1&case_id="+row["Case ID"]+"&tab=reports")
    finally:db.close()

def test_display_preview_twelve_rows_but_aggregate_counts_cover_all():
    cases=[Obj(id=i,status="OPEN",source_type="SOCIAL",source_id=str(i),
               source_url="https://example.invalid/"+str(i)) for i in range(1,19)]
    summary=officer_pilot_readiness(cases,{},[])
    assert summary["authorized_case_count"]==18
    assert len(summary["case_preview"])==12
    assert summary["case_preview_is_sample"] is True
    assert summary["worksheet_full_cohort_available"] is True
    assert [row["case_id"] for row in summary["case_preview"]]==list(range(1,13))
    assert summary["five_stage_observed_case_count"]==0

def test_preview_observation_count_matches_aggregate_stage_counts():
    db=officer_dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        r=build_briefing(db,profile(db,_user(db,1)),1)
        summary=r["officer_pilot_readiness"]
        assert summary["authorized_case_count"]==len(summary["case_preview"])==1
        assert summary["stage_counts"]=={
            k:sum(int(row["observed_stages"][k]) for row in summary["case_preview"])
            for k in STAGES}
        assert summary["case_preview"][0]["observed_stage_count"]==2
        assert r["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_invalid_period_rejected_via_existing_casework_validation():
    db=management_dataset()
    try:
        with pytest.raises(HTTPException) as exc:
            export(db,2,period="all_time")
        assert exc.value.status_code==422
    finally:db.close()

def test_excessive_topic_rejected_and_not_used_for_broad_exports():
    db=management_dataset()
    try:
        with pytest.raises(HTTPException) as exc:
            export(db,1,topic="x"*125)
        assert exc.value.status_code==422
    finally:db.close()

def test_export_does_not_write_to_casework_tables_or_call_model():
    db=management_dataset()
    queries=[]
    def record(conn,cursor,statement,params,context,executemany):
        queries.append(statement.lstrip().lower())
    event.listen(db.get_bind(),"before_cursor_execute",record)
    try:
        resp=export(db,1)
        assert resp.headers["x-pilot-data-basis"]=="AUTHORIZED_CASEWORK_WINDOW_AUDIT"
        assert not any(x.startswith(("insert ","update ","delete ")) for x in queries)
        assert "SYNTHETIC_APPROVED" not in resp.body.decode("utf-8-sig")
    finally:
        event.remove(db.get_bind(),"before_cursor_execute",record)
        db.close()
