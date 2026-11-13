"""v153.9: one management case classifier and permission-scoped empty-case reporting.

All fixtures are isolated in memory. These tests do not write to live Supabase.
The data model matches the existing three tables inspected read-only in staging.
"""
import pytest
from types import SimpleNamespace as Obj
from json import dumps

from app.management_investigation_readiness import (
    classify_case_readiness,investigation_readiness_board)
from app.management_followup_queue import management_followup_queue
from app.management_reporting import build_briefing
from app.access import profile
from app.models import User
from app.casework import CaseAssignment,CaseReport,CaseTransition
from test_management_briefings_v1468 import dataset
from test_management_followup_v1536 import case,report,review

def pair(cases,reports=None,events=None):
    cases=list(cases)
    reports=reports or {}
    events=events or []
    return (investigation_readiness_board(cases,reports,events),
            management_followup_queue(cases,reports,events))

def check_action(one_case,expected,group,reports=None,events=None):
    readiness,queue=pair([one_case],reports,events)
    assert readiness["review_attention_count"]==queue["attention_count"]==1
    assert len(readiness["preview"])==len(queue["items"])==1
    r=readiness["preview"][0];q=queue["items"][0]
    assert r["group"]==q["aligned_readiness_group"]==group
    assert r["reason_code"]==q["aligned_readiness_reason"]
    assert q["action_code"]==expected
    assert r["case_id"]==q["case_id"]
    assert r["source_check_attested_in_window"]==q["source_review_attested_in_window"]
    assert r["source_review_observed_in_window"]==q["latest_source_review_observed_in_window"]
    assert q["reconciliation_is_workflow_only"] is True
    return r,q

def test_submitted_without_visible_source_event_needs_history_not_premature_review():
    r,q=check_action(case(),"CHECK_HISTORICAL_SOURCE_REVIEW","REVIEW_HISTORY_CHECK",
                     reports={1:report("SUBMITTED")})
    assert not q["source_review_attested_in_window"]
    assert q["responsible_role_hint"]=="ASSIGNED_OFFICER"
    assert q["priority"]=="P2"

def test_submitted_with_source_unavailable_requires_source_recheck_first():
    r,q=check_action(case(),"SOURCE_REVIEW_RECHECK","EVIDENCE_RECHECK",
                     reports={1:report("SUBMITTED")},
                     events=[review(status="SOURCE_UNAVAILABLE",opened=False)])
    assert q["priority"]=="P1"
    assert r["reason_code"]=="SUBMITTED_WITH_UNRESOLVED_WINDOW_SOURCE_REVIEW"

def test_submitted_with_last_source_attestation_can_request_independent_review():
    r,q=check_action(case(),"INDEPENDENT_REPORT_REVIEW","INDEPENDENT_REVIEW",
                     reports={1:report("SUBMITTED")},events=[review()])
    assert q["responsible_role_hint"]=="INDEPENDENT_REVIEWER"
    assert r["ready_for_independent_review_is_legal_approval"] is False

def test_last_source_event_overrides_an_earlier_valid_check():
    broken=Obj(id=99,case_id=1,action="SOURCE_REVIEW_RECORDED",
        details_json=dumps({"status":"NEEDS_INFORMATION","original_source_opened":False}))
    check_action(case(),"SOURCE_REVIEW_RECHECK","EVIDENCE_RECHECK",
                 reports={1:report("SUBMITTED")},events=[review(),broken])

def test_submitted_report_with_malformed_source_audit_event_does_not_approve():
    corrupted=Obj(id=12,case_id=1,action="SOURCE_REVIEW_RECORDED",
                  details_json='["untrusted", "record"]')
    check_action(case(),"SOURCE_REVIEW_RECHECK","EVIDENCE_RECHECK",
                 reports={1:report("SUBMITTED")},events=[corrupted])

def test_approved_report_still_open_is_reconciliation_not_workflow_complete():
    r,q=check_action(case(status="OPEN"),"RECONCILE_CASE_REPORT_STATUS",
                     "OTHER_FOLLOWUP",reports={1:report("APPROVED")})
    assert r["reason_code"]=="APPROVED_REPORT_WITH_UNRESOLVED_CASE_STATUS"
    assert q["priority"]=="P1"
    assert q["responsible_role_hint"]=="AUTHORIZED_CASEWORK_REVIEWER"

def test_approved_report_with_case_needing_information_is_reconciliation():
    check_action(case(status="NEEDS_INFORMATION"),"RECONCILE_CASE_REPORT_STATUS",
                 "OTHER_FOLLOWUP",reports={1:report("APPROVED")})

def test_approved_report_in_review_is_complete_only_as_workflow_state():
    readiness,queue=pair([case()],reports={1:report("APPROVED")})
    assert readiness["group_counts"]["WORKFLOW_COMPLETE"]==1
    assert queue["attention_count"]==0
    assert readiness["legal_violation_confirmed"] is False

def test_closed_case_submitted_report_is_excluded_without_creating_work():
    readiness,queue=pair([case(status="CLOSED")],reports={1:report("SUBMITTED")})
    assert readiness["review_attention_count"]==0
    assert queue["closed_cases_excluded"]==1

def test_unaccepted_assignment_recommends_officer_acceptance():
    check_action(case(status="ASSIGNED"),"RECEIVING_TEAM_ACCEPTANCE","OFFICER_ACTION")

def test_unfinished_information_request_recommends_casework_followup():
    check_action(case(status="NEEDS_INFORMATION"),"CASE_INFORMATION_FOLLOWUP",
                 "OFFICER_ACTION")

def test_checked_source_without_report_recommends_officer_report():
    check_action(case(),"CREATE_OFFICER_REPORT","OFFICER_ACTION",events=[review()])

def test_checked_source_with_returned_report_requires_revision():
    check_action(case(),"SUBMIT_OR_REVISE_LATEST_REPORT","OFFICER_ACTION",
                 reports={1:report("RETURNED")},events=[review()])

def test_unknown_status_routes_reconciliation_without_fabricating_clearance():
    check_action(case(status="INVALID_STATE"),"RECONCILE_CASE_REPORT_STATUS",
                 "OTHER_FOLLOWUP",reports={1:report("INVALID_REPORT")},events=[review()])

def test_cross_view_counts_cover_all_cases_not_only_first_twelve():
    rows=[case(i,status="OPEN" if i%2 else "IN_REVIEW") for i in range(1,19)]
    r,q=pair(rows)
    assert r["review_attention_count"]==q["attention_count"]==18
    assert len(r["preview"])==len(q["items"])==12
    assert r["preview_is_sample"] and q["preview_is_sample"]
    assert sum(r["group_counts"].values())==18
    assert sum(q["priority_counts"].values())==18
    assert r["group_counts"]["OFFICER_ACTION"]==9
    assert r["group_counts"]["REVIEW_HISTORY_CHECK"]==9

def test_readiness_and_queue_cover_every_known_case_state_and_report_state():
    cases=[]
    reports={}
    events=[]
    case_states=["OPEN","ASSIGNED","IN_REVIEW","NEEDS_INFORMATION","CLOSED"]
    report_states=["NO_REPORT","DRAFT","SUBMITTED","RETURNED","APPROVED"]
    for i,state in enumerate(case_states):
        for j,report_status in enumerate(report_states):
            num=i*len(report_states)+j+1
            cases.append(case(num,status=state))
            if report_status!="NO_REPORT":
                reports[num]=report(report_status)
            if num%3==0:
                record=review(num,status="SOURCE_UNAVAILABLE",opened=False)
                record.id=num
                events.append(record)
            elif num%3==1:
                record=review(num)
                record.id=num
                events.append(record)
    readiness,queue=pair(cases,reports,events)
    assert readiness["authorized_case_count"]==25
    assert readiness["review_attention_count"]==queue["attention_count"]
    assert sum(readiness["group_counts"].values())==25
    assert sum(queue["priority_counts"].values())==queue["attention_count"]
    assert all(x["recommended_action_is_assignment"] is False for x in queue["items"])
    assert readiness["paid_ai_calls"]==0
    assert queue["additional_database_queries"]==0

def test_realistic_province_fixture_keeps_counts_consistent():
    db=dataset()
    try:
        for uid,expected in ((1,3),(2,2),(3,1)):
            r=build_briefing(db,profile(db,db.get(User,uid)),uid,language="en")
            check=r["management_consistency"]
            assert check["schema"]=="BAWASLU_MANAGEMENT_CASEWORK_RECONCILIATION_V1539"
            assert check["authorized_cases_in_window"]==expected
            assert check["followup_readiness_counts_match"] is True
            assert check["followup_attention_count"]==check["readiness_attention_count"]
            assert check["real_casework_sample_available"] is True
            assert check["automatic_casework_actions_created"] is False
            assert r["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_empty_casework_population_is_neither_success_nor_acceptance():
    db=dataset()
    try:
        db.query(CaseTransition).delete()
        db.query(CaseReport).delete()
        db.query(CaseAssignment).delete()
        db.commit()
        r=build_briefing(db,profile(db,db.get(User,1)),1,language="en")
        check=r["management_consistency"]
        assert check["authorized_cases_in_window"]==0
        assert check["real_casework_sample_available"] is False
        assert check["followup_readiness_counts_match"] is True
        assert check["sample_is_not_formal_officer_acceptance"] is True
        assert r["investigation_readiness"]["review_attention_count"]==0
        assert r["followup_queue"]["attention_count"]==0
        assert r["metrics"]["assignments"]==0
        assert r["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_report_reconciliation_uses_real_case_sql_columns_only():
    assert CaseAssignment.__tablename__=="case_assignments"
    assert CaseReport.__tablename__=="case_reports"
    assert CaseTransition.__tablename__=="case_transitions"
    assert {CaseAssignment.id.key,CaseAssignment.status.key,CaseAssignment.created_at.key}=={
        "id","status","created_at"}
    assert {CaseReport.case_id.key,CaseReport.created_at.key,CaseReport.status.key}=={
        "case_id","created_at","status"}

def test_management_queue_excludes_raw_source_text_and_audit_notes():
    c=case()
    r,q=pair([c],events=[review()])
    for phrase in ("SENSITIVE_ORIGINAL_TEXT","SENSITIVE_PRIVATE_CASE_NOTE","SENSITIVE_AUDIT_NOTE"):
        assert phrase not in str(r)
        assert phrase not in str(q)
    assert q["source_truth_verified"] is False
    assert q["legal_verdict_confirmed"] is False

def test_per_case_classification_matches_shared_helper():
    c=case()
    selected_report=report("SUBMITTED")
    latest_event=review()
    direct=classify_case_readiness(c,selected_report,latest_event)
    readiness,queue=pair([c],reports={1:selected_report},events=[latest_event])
    assert readiness["preview"][0]["group"]==direct[0]
    assert queue["items"][0]["aligned_readiness_reason"]==direct[1]
    assert queue["items"][0]["source_review_attested_in_window"]==direct[-1]

def test_submitted_report_draft_does_not_instruct_unchecked_independent_approval():
    db=dataset()
    try:
        from datetime import datetime
        from app.casework import CaseReport
        # The fixture contains an OPEN case with approved report; move the
        # report to SUBMITTED only inside this isolated test database.
        db.query(CaseReport).filter(CaseReport.case_id==1).update({"status":"SUBMITTED"})
        db.commit()
        r=build_briefing(db,profile(db,db.get(User,2)),2,language="en")
        actions=" ".join(r["template"]["recommended_actions"])
        assert "Before routing" in actions
        assert "Submission alone does not prove verification" in actions
        assert "Inspect historical audit records" in actions
        assert r["followup_queue"]["items"][0]["action_code"]=="CHECK_HISTORICAL_SOURCE_REVIEW"
        assert r["investigation_readiness"]["group_counts"]["REVIEW_HISTORY_CHECK"]>=1
        assert r["management_consistency"]["followup_readiness_counts_match"] is True
    finally:
        db.close()

def test_new_management_metadata_does_not_claim_automated_case_actions():
    db=dataset()
    try:
        snapshot=build_briefing(db,profile(db,db.get(User,1)),1,language="en")
        assert snapshot["management_consistency"]["legal_verdict_confirmed"] is False
        assert snapshot["management_consistency"]["automatic_casework_actions_created"] is False
        assert snapshot["followup_queue"]["automatic_casework_actions_created"] is False
        assert snapshot["investigation_readiness"]["any_case_assigned_or_updated"] is False
    finally:db.close()
