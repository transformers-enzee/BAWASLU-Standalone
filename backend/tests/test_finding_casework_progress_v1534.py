"""v153.4 Command Centre uses actual officer audit history and authorized casework."""
from datetime import datetime,timedelta
from sqlalchemy import event
from app.casework import (
    CaseAssignment,CaseTransition,NewCase,SourceReviewAction,ReportAction,
    acknowledge_case,record_source_review,create_report,transition_report,
)
from app.finding_assessments import contextual_casework_links
from app.finding_case_progress import summarize_authorized_case_progress
from app.management_reporting import build_briefing,_casework_evidence_progress
from test_casework_workflow import dataset,confirmed
from test_officer_acceptance_v1480 import _user,_case,_review,_report
from test_officer_followup_v1477 import evidence,permission

def progress(db,case_id):
    return summarize_authorized_case_progress(db,[db.get(CaseAssignment,case_id)])[case_id]

def t(trace,key):
    return next(x["done"] for x in trace["steps"] if x["key"]==key)

def test_empty_case_progress_does_not_query_or_fabricate():
    db=dataset()
    try:
        assert summarize_authorized_case_progress(db,[])=={}
    finally:db.close()

def test_existing_case_has_one_real_audit_stage_and_no_source_verdict():
    db=dataset()
    try:
        case=_case(db)
        row=progress(db,case["id"])
        assert row["schema"]=="BAWASLU_CASEWORK_AUDIT_PROGRESS_V1534"
        assert row["completed_steps"]==1
        assert row["total_steps"]==5
        assert t(row,"source_linked") is True
        assert t(row,"original_source_checked") is False
        assert row["source_truth_verified"] is False
        assert row["human_acceptance_certified"] is False
        assert row["latest_report_status"]=="NO_REPORT"
        assert row["next_uncompleted_step"]=="receiving_officer_accepted"
    finally:db.close()

def test_officer_acceptance_and_source_review_increase_audit_progress():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        assert progress(db,case["id"])["completed_steps"]==2
        record_source_review(case["id"],_review(),_user(db,2),db)
        row=progress(db,case["id"])
        assert row["completed_steps"]==3
        assert row["latest_source_review_status"]=="SOURCE_CHECKED"
        assert t(row,"original_source_checked") is True
        assert row["casework_progress_is_legal_verdict"] is False
    finally:db.close()

def test_unavailable_source_is_not_represented_as_checked():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(
            status="SOURCE_UNAVAILABLE",opened=False,
            note="I could not retrieve the original source from the saved link."),
            _user(db,2),db)
        row=progress(db,case["id"])
        assert row["latest_source_review_status"]=="SOURCE_UNAVAILABLE"
        assert t(row,"original_source_checked") is False
        assert row["completed_steps"]==2
    finally:db.close()

def test_needs_information_is_a_real_officer_review_status():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(
            status="NEEDS_INFORMATION",opened=False,
            note="The source attribution needs independent verification."),
            _user(db,2),db)
        row=progress(db,case["id"])
        assert row["latest_source_review_status"]=="NEEDS_INFORMATION"
        assert not t(row,"original_source_checked")
    finally:db.close()

def test_latest_report_and_independent_approval_require_actual_events():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        report=create_report(case["id"],_report(),_user(db,2),db)
        assert not t(progress(db,case["id"]),"latest_report_submitted")
        transition_report(report["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        submitted=progress(db,case["id"])
        assert submitted["completed_steps"]==4
        assert submitted["latest_report_status"]=="SUBMITTED"
        transition_report(report["id"],ReportAction(status="APPROVED"),_user(db,1),db)
        approved=progress(db,case["id"])
        assert approved["completed_steps"]==5
        assert all(s["done"] for s in approved["steps"])
        assert approved["latest_report_status"]=="APPROVED"
        assert approved["human_acceptance_certified"] is False
    finally:db.close()

def test_new_report_version_does_not_inherit_old_submission():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        first=create_report(case["id"],_report(),_user(db,2),db)
        transition_report(first["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        create_report(case["id"],_report(),_user(db,2),db)
        row=progress(db,case["id"])
        assert row["latest_report_status"]=="DRAFT"
        assert t(row,"latest_report_submitted") is False
        assert row["latest_report_version_only"] is True
    finally:db.close()

def test_authorized_finding_handoff_has_progress_not_raw_audit_note():
    db=dataset()
    try:
        case=_case(db)
        record_count=db.query(CaseTransition).count()
        action=contextual_casework_links(db,permission(db,2),2,evidence())["source_actions"][0]
        row=action["workflow_progress"]
        assert action["existing_case_id"]==case["id"]
        assert row["case_id"]==case["id"]
        assert row["completed_steps"]==1
        assert "latest_source_review_note" not in row
        assert "events" not in row
        assert db.query(CaseTransition).count()==record_count
    finally:db.close()

def test_unrelated_province_does_not_receive_case_progress():
    db=dataset()
    try:
        case=_case(db)
        action=contextual_casework_links(db,permission(db,3),3,evidence())["source_actions"][0]
        assert action["existing_case_id"] is None
        assert action["workflow_progress"] is None
        assert "case_id=" not in str(action["casework_url"])
    finally:db.close()

def test_forged_ids_never_create_workflow_progress_or_case_url():
    db=dataset()
    try:
        _case(db)
        altered=evidence(source="11%26case_id%3D999",campaign="90")
        result=contextual_casework_links(db,permission(db,1),1,altered)
        assert result["source_actions"]==[]
    finally:db.close()

def test_two_bounded_audit_queries_for_authorized_case_progress():
    db=dataset()
    try:
        case=_case(db)
        queries=[]
        def record(conn,cursor,statement,params,context,executemany):
            text=statement.lower()
            if "case_transitions" in text or "case_reports" in text:
                queries.append(text)
        event.listen(db.get_bind(),"before_cursor_execute",record)
        try:
            progress(db,case["id"])
        finally:
            event.remove(db.get_bind(),"before_cursor_execute",record)
        assert sum("case_transitions" in s for s in queries)==1
        assert sum("case_reports" in s for s in queries)==1
    finally:db.close()

def test_reporting_distinguishes_not_observed_from_never_reviewed():
    db=dataset()
    try:
        _case(db)
        snap=build_briefing(db,permission(db,1),1,now=datetime.utcnow()+timedelta(minutes=2),language="en")
        result=snap["casework_progress"]
        assert result["authorized_assignments"]==1
        assert result["source_check_attested_in_window"]==0
        assert result["source_review_event_not_observed_in_window"]==1
        assert result["missing_event_does_not_mean_never_reviewed"] is True
        assert result["additional_database_queries"]==0
        assert snap["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_reporting_counts_actual_checked_attestation_and_not_legal_truth():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        snap=build_briefing(db,permission(db,1),1,now=datetime.utcnow()+timedelta(minutes=2),language="en")
        result=snap["casework_progress"]
        assert result["source_check_attested_in_window"]==1
        assert result["source_review_requires_attention_in_window"]==0
        assert result["source_review_event_not_observed_in_window"]==0
        assert result["legal_verdict_confirmed"] is False
        assert "audited original-source check" in snap["template"]["executive_summary"]
    finally:db.close()

def test_latest_source_review_reverses_earlier_checked_status():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        record_source_review(case["id"],_review(
            status="NEEDS_INFORMATION",opened=False,
            note="The saved post requires new context and verified attribution."),
            _user(db,2),db)
        snap=build_briefing(db,permission(db,1),1,now=datetime.utcnow()+timedelta(minutes=2),language="en")
        result=snap["casework_progress"]
        assert result["source_check_attested_in_window"]==0
        assert result["source_review_requires_attention_in_window"]==1
    finally:db.close()

def test_reporting_recommends_followup_for_unaccepted_or_pending_report():
    db=dataset()
    try:
        case=_case(db)
        snap=build_briefing(db,permission(db,1),1,now=datetime.utcnow()+timedelta(minutes=2),language="en")
        actions=snap["template"]["recommended_actions"]
        assert any("receiving-officer acceptance" in x for x in actions)
        acknowledge_case(case["id"],_user(db,2),db)
        report=create_report(case["id"],_report(),_user(db,2),db)
        transition_report(report["id"],ReportAction(status="SUBMITTED"),_user(db,2),db)
        snap=build_briefing(db,permission(db,1),1,now=datetime.utcnow()+timedelta(minutes=2),language="en")
        assert snap["casework_progress"]["latest_report_awaiting_approval"]==1
        assert any("independent reviewers" in x for x in snap["template"]["recommended_actions"])
    finally:db.close()

def test_reporting_empty_authorized_scope_has_zero_progress():
    db=dataset()
    try:
        _case(db)
        snap=build_briefing(db,permission(db,3),3,now=datetime.utcnow()+timedelta(minutes=2),language="en")
        result=snap["casework_progress"]
        assert result["authorized_assignments"]==0
        assert result["source_check_attested_in_window"]==0
        assert result["source_review_event_not_observed_in_window"]==0
        assert result["created_casework_actions"] is False
    finally:db.close()
