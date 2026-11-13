"""v154.0: officer-pilot readiness, audited case history, zero live-case claims.

Tests run against isolated in-memory SQLite fixtures only, not live Supabase.
"""
import json
from datetime import datetime,timedelta
from io import BytesIO
from types import SimpleNamespace as Obj

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader
from sqlalchemy import event

from app.access import profile
from app.casework import (
    CaseAssignment,CaseReport,CaseTransition,ReportAction,
    acknowledge_case,case_detail,create_report,record_source_review,
    transition_report,
)
from app.management_reporting import build_briefing
from app.models import User
from app.officer_pilot_readiness import officer_pilot_readiness
from app.management_report_templates import render_docx,render_pdf,render_xlsx
from test_management_briefings_v1468 import dataset as report_dataset
from test_casework_workflow import dataset
from test_officer_acceptance_v1480 import _user,_case,_review,_report

def snapshot(db,user_id=1,lang="en"):
    return build_briefing(db,profile(db,db.get(User,user_id)),user_id,
                          now=datetime.utcnow()+timedelta(minutes=2),language=lang)

def pilot(db,uid=1):
    return snapshot(db,uid)["officer_pilot_readiness"]

def test_empty_input_explicitly_requires_real_cases():
    result=officer_pilot_readiness([],{},[])
    assert result["authorized_case_count"]==0
    assert result["real_casework_available_in_scope"] is False
    assert result["five_stage_observed_case_count"]==0
    assert result["authorized_human_signoff_received"] is False
    assert result["next_steps"][0]=="WAIT_FOR_AUTHORIZED_REAL_CASES"

def test_initial_real_case_does_not_infer_officer_acceptance_from_created_status():
    db=dataset()
    try:
        case=_case(db)
        result=pilot(db)
        assert result["authorized_case_count"]==1
        assert result["stage_counts"]["source_linked"]==1
        assert result["stage_counts"]["receiving_officer_accepted"]==0
        assert result["stage_counts"]["original_source_checked"]==0
        assert result["five_stage_observed_case_count"]==0
        assert result["automated_pilot_acceptance_granted"] is False
    finally:db.close()

def test_actual_receiving_officer_acceptance_observed_in_audit():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        result=pilot(db)
        assert result["stage_counts"]["receiving_officer_accepted"]==1
        assert result["stage_counts"]["source_linked"]==1
        assert result["stage_counts"]["original_source_checked"]==0
    finally:db.close()

def test_actual_source_check_is_recorded_without_claiming_legal_truth():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        result=pilot(db)
        assert result["stage_counts"]["original_source_checked"]==1
        assert result["source_authenticity_verified"] is False
        assert result["legal_verdict_confirmed"] is False
    finally:db.close()

def test_source_unavailable_never_counts_as_verified_source_check():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(
            status="SOURCE_UNAVAILABLE",opened=False,
            note="The original post is inaccessible; evidence remains unresolved."),_user(db,2),db)
        result=pilot(db)
        assert result["stage_counts"]["original_source_checked"]==0
        assert result["five_stage_observed_case_count"]==0
    finally:db.close()

def test_submitted_report_requires_actual_submission_audit_event():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        report=create_report(case["id"],_report(),_user(db,2),db)
        before=pilot(db)
        assert before["stage_counts"]["latest_report_submitted"]==0
        transition_report(report["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        after=pilot(db)
        assert after["stage_counts"]["latest_report_submitted"]==1
        assert after["stage_counts"]["independent_report_approval"]==0
        assert after["five_stage_observed_case_count"]==0
    finally:db.close()

def test_full_audited_path_is_observed_but_never_formally_accepted():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        report=create_report(case["id"],_report(),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="APPROVED"),_user(db,1),db)
        result=pilot(db)
        assert result["stage_counts"]=={
            "source_linked":1,"receiving_officer_accepted":1,
            "original_source_checked":1,"latest_report_submitted":1,
            "independent_report_approval":1}
        assert result["five_stage_observed_case_count"]==1
        assert result["authorized_human_signoff_received"] is False
        assert result["automated_pilot_acceptance_granted"] is False
        assert result["complete_trace_is_not_formal_acceptance"] is True
        assert snapshot(db)["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_subsequent_source_recheck_reverses_observed_complete_case():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        report=create_report(case["id"],_report(),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="APPROVED"),_user(db,1),db)
        assert pilot(db)["five_stage_observed_case_count"]==1
        record_source_review(case["id"],_review(
            status="NEEDS_INFORMATION",opened=False,
            note="The original source needs further attribution verification."),_user(db,2),db)
        updated=pilot(db)
        assert updated["five_stage_observed_case_count"]==0
        assert updated["stage_counts"]["original_source_checked"]==0
    finally:db.close()

def test_latest_report_version_must_have_its_own_submission():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        first=create_report(case["id"],_report(),_user(db,2),db)
        transition_report(first["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        create_report(case["id"],_report(),_user(db,2),db)
        result=pilot(db)
        assert result["stage_counts"]["latest_report_submitted"]==0
    finally:db.close()

def test_oldest_200_audit_events_no_longer_hide_latest_source_review():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        for n in range(205):
            db.add(CaseTransition(case_id=case["id"],actor_id=2,
                action="COMMENT_LOGGED",details_json=json.dumps({"n":n})))
        db.commit()
        record_source_review(case["id"],_review(
            status="SOURCE_UNAVAILABLE",opened=False,
            note="The latest review cannot retrieve the original post."),_user(db,2),db)
        detail=case_detail(case["id"],_user(db,2),db)
        assert len(detail["events"])==200
        ids=[row["id"] for row in detail["events"]]
        assert ids==sorted(ids)
        assert detail["workflow_trace"]["latest_source_review_status"]=="SOURCE_UNAVAILABLE"
        assert detail["workflow_trace"]["steps"][2]["done"] is False
        assert detail["workflow_trace"]["event_window_limited"] is True
        assert all(event["action"]!="CREATED" for event in detail["events"])
    finally:db.close()

def test_last_two_hundred_audit_events_still_contain_most_recent_positive_review():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        for n in range(202):
            db.add(CaseTransition(case_id=case["id"],actor_id=2,
                action="COMMENT_LOGGED",details_json="{}"))
        db.commit()
        record_source_review(case["id"],_review(),_user(db,2),db)
        d=case_detail(case["id"],_user(db,2),db)
        assert d["workflow_trace"]["latest_source_review_status"]=="SOURCE_CHECKED"
        assert d["workflow_trace"]["steps"][2]["done"] is True
    finally:db.close()

def test_stage_counts_do_not_confuse_separate_cases_with_one_complete_path():
    one=Obj(id=1,source_id="1",source_url="https://example.invalid/1",
            source_type="SOCIAL",status="IN_REVIEW")
    two=Obj(id=2,source_id="2",source_url="https://example.invalid/2",
            source_type="SOCIAL",status="IN_REVIEW")
    events=[Obj(id=1,case_id=1,action="CREATED",details_json="{}"),
            Obj(id=2,case_id=2,action="ACKNOWLEDGED",details_json="{}")]
    result=officer_pilot_readiness([one,two],{},events)
    assert result["stage_counts"]["source_linked"]==1
    assert result["stage_counts"]["receiving_officer_accepted"]==1
    assert result["five_stage_observed_case_count"]==0

def test_province_scope_in_report_readiness():
    db=report_dataset()
    try:
        expected={1:3,2:2,3:1}
        for uid,n in expected.items():
            result=snapshot(db,uid)["officer_pilot_readiness"]
            assert result["authorized_case_count"]==n
            assert result["five_stage_observed_case_count"]==0
            assert result["paid_model_calls"]==0
    finally:db.close()

def test_no_casework_no_false_acceptance_or_success_in_english_and_indonesian():
    db=report_dataset()
    try:
        db.query(CaseTransition).delete()
        db.query(CaseReport).delete()
        db.query(CaseAssignment).delete()
        db.commit()
        en=snapshot(db,1,"en")
        ind=snapshot(db,1,"id")
        assert en["officer_pilot_readiness"]["authorized_case_count"]==0
        assert en["officer_pilot_readiness"]["automated_pilot_acceptance_granted"] is False
        assert en["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
        assert "No real officer casework is available" in en["template"]["executive_summary"]
        assert "Tidak ada penugasan petugas riil" in ind["template"]["executive_summary"]
        assert "select an authorized real case" in " ".join(en["template"]["recommended_actions"])
    finally:db.close()

def test_no_casework_preserves_existing_no_saved_assignments_first_action():
    db=report_dataset()
    try:
        db.query(CaseTransition).delete()
        db.query(CaseReport).delete()
        db.query(CaseAssignment).delete()
        db.commit()
        output=snapshot(db,1,"en")["template"]
        assert output["recommended_actions"][0].startswith("No saved assignments")
        assert any("Before formal acceptance" in item for item in output["recommended_actions"][1:])
        assert output["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_management_exports_preserve_officer_acceptance_caveat():
    db=report_dataset()
    try:
        temp=snapshot(db,2)["template"]
        assert temp["officer_pilot_evidence"]["authorized_human_signoff_received"] is False
        assert temp["officer_pilot_evidence"]["five_stage_observed_case_count"]==0
        word=Document(BytesIO(render_docx(temp)))
        assert "not formal acceptance" in " ".join(x.text for x in word.paragraphs)
        pdf=PdfReader(BytesIO(render_pdf(temp)))
        import re
        txt=" ".join(" ".join(x.extract_text() or "" for x in pdf.pages).split())
        assert re.search("not formal acceptance",txt,re.I)
        workbook=load_workbook(BytesIO(render_xlsx(temp)),read_only=True)
        values=" ".join(str(cell) for row in workbook["Report Summary"].values for cell in row if cell is not None)
        assert "not formal acceptance" in values
    finally:db.close()

def test_reporting_is_read_only_and_has_no_extra_sql_queries():
    db=report_dataset()
    statements=[]
    def record(conn,cursor,statement,params,context,executemany):
        statements.append(statement.lower().lstrip())
    event.listen(db.get_bind(),"before_cursor_execute",record)
    try:
        result=snapshot(db,1)
        assert result["officer_pilot_readiness"]["no_new_sql_queries"] is True
        assert not any(s.startswith(("insert ","update ","delete ")) for s in statements)
        assert result["officer_pilot_readiness"]["no_casework_writes"] is True
    finally:
        event.remove(db.get_bind(),"before_cursor_execute",record)
        db.close()

def test_non_audit_status_not_equivalent_to_full_observed_workflow():
    db=report_dataset()
    try:
        result=pilot(db,2)
        # Fixture case 1 has an APPROVED report but no matching approval and
        # report-submission audit events. Stage counts must remain zero.
        assert result["stage_counts"]["independent_report_approval"]==0
        assert result["stage_counts"]["latest_report_submitted"]==0
    finally:db.close()
