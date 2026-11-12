"""v148.0: real officer acceptance workflow, tested with isolated fixtures.

Never writes to the live Supabase database, creates a fictitious real case,
or misrepresents a source review as evidence truth or a legal judgment.
"""
import json
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models import User,AccessGrant
from app.access import default_permissions
from app.casework import (
    CaseAssignment,CaseTransition,CaseReport,
    NewCase,SourceReviewAction,ReportDraft,ReportAction,RouteCase,
    create_case,acknowledge_case,record_source_review,create_report,
    transition_report,case_detail,route_case,
)
from test_casework_workflow import dataset,confirmed


def _user(db,ident):
    return db.get(User,ident)


def _case(db):
    confirmed(db)
    return create_case(NewCase(source_type="SOCIAL",source_id="11",campaign_id=90,
        department="Penanganan Pelanggaran",target_scope="PROVINCE",
        target_province="Riau",assignee_id=2),
        _user(db,1),db)


def _review(status="SOURCE_CHECKED",opened=True,
            note="I opened the original and checked the post context and date."):
    return SourceReviewAction(status=status,
        note=note,original_source_opened=opened)


def _report():
    return ReportDraft(title="Riau source-linked oversight review",
        executive_summary="One saved source was examined by an officer.",
        findings="Allegation noted. Neither content truth nor legal violation is established.",
        verification_notes="Original post opened; attribution and legal elements remain unresolved.",
        recommendations="Seek documentary confirmation before any legal escalation.")


def test_full_audited_casework_path_requires_human_review_and_separate_approval():
    db=dataset()
    try:
        case=_case(db)
        case_id=case["id"]
        initial=case_detail(case_id,_user(db,2),db)
        assert initial["workflow_trace"]["completed"]==1
        assert initial["workflow_trace"]["total"]==5
        assert initial["workflow_trace"]["workflow_trace_complete"] is False
        assert initial["can_record_source_review"] is False

        accepted=acknowledge_case(case_id,_user(db,2),db)
        assert accepted["status"]=="IN_REVIEW"
        progress=case_detail(case_id,_user(db,2),db)
        assert progress["can_record_source_review"] is True
        assert progress["workflow_trace"]["completed"]==2

        source=record_source_review(case_id,_review(),_user(db,2),db)
        assert source["status"]=="SOURCE_CHECKED"
        assert source["requires_separate_legal_assessment"] is True
        trace=case_detail(case_id,_user(db,2),db)["workflow_trace"]
        assert trace["completed"]==3
        assert trace["latest_source_review_status"]=="SOURCE_CHECKED"
        assert trace["evidence_source_is_confirmed_true"] is False
        assert trace["legal_violation_determined"] is False

        report=create_report(case_id,_report(),_user(db,2),db)
        submitted=transition_report(report["id"],ReportAction(status="SUBMITTED"),
                                    _user(db,2),db)
        assert submitted["status"]=="SUBMITTED"
        trace=case_detail(case_id,_user(db,1),db)["workflow_trace"]
        assert trace["completed"]==4
        assert trace["steps"][-1]["done"] is False

        with pytest.raises(HTTPException) as denied:
            transition_report(report["id"],ReportAction(status="APPROVED"),_user(db,2),db)
        assert denied.value.status_code==403

        approved=transition_report(report["id"],ReportAction(status="APPROVED"),
                                   _user(db,1),db)
        assert approved["reviewed_by"]==1 and approved["created_by"]==2
        final=case_detail(case_id,_user(db,2),db)
        acceptance=final["workflow_trace"]
        assert acceptance["completed"]==5
        assert acceptance["total"]==5
        assert acceptance["workflow_trace_complete"] is True
        assert all(item["done"] for item in acceptance["steps"])
        assert acceptance["client_acceptance_certified"] is False
        assert acceptance["legal_violation_determined"] is False
        assert acceptance["paid_provider_called"] is False
        events=final["events"]
        assert [e["action"] for e in events if e["action"] in {
            "CREATED","ACKNOWLEDGED","SOURCE_REVIEW_RECORDED",
            "REPORT_SUBMITTED","REPORT_APPROVED"}]==[
            "CREATED","ACKNOWLEDGED","SOURCE_REVIEW_RECORDED",
            "REPORT_SUBMITTED","REPORT_APPROVED"]
        assert any(e["details"].get("not_a_content_or_legal_verdict") is True
                   for e in events if e["action"]=="SOURCE_REVIEW_RECORDED")
    finally:
        db.close()


def test_no_source_check_without_opening_original_or_available_link():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        with pytest.raises(HTTPException) as err:
            record_source_review(case["id"],_review(opened=False),_user(db,2),db)
        assert err.value.status_code==422
        assert db.query(CaseTransition).filter_by(
            case_id=case["id"],action="SOURCE_REVIEW_RECORDED").count()==0

        db.get(CaseAssignment,case["id"]).source_url=""
        db.commit()
        with pytest.raises(HTTPException) as err:
            record_source_review(case["id"],_review(),_user(db,2),db)
        assert err.value.status_code==422
        recorded=record_source_review(case["id"],_review(
            status="SOURCE_UNAVAILABLE",opened=False,
            note="The original URL is no longer accessible and requires an alternative source."),
            _user(db,2),db)
        assert recorded["status"]=="SOURCE_UNAVAILABLE"
        trace=case_detail(case["id"],_user(db,2),db)["workflow_trace"]
        assert trace["steps"][2]["done"] is False
        assert trace["latest_source_review_status"]=="SOURCE_UNAVAILABLE"
    finally:
        db.close()


def test_only_current_assigned_receiving_officer_can_record_review():
    db=dataset()
    try:
        case=_case(db)
        # No source review before receiving officer explicitly accepts it.
        with pytest.raises(HTTPException) as err:
            record_source_review(case["id"],_review(),_user(db,2),db)
        assert err.value.status_code==403
        acknowledge_case(case["id"],_user(db,2),db)

        for unauthorized in (1,3,4):
            with pytest.raises(HTTPException) as err:
                record_source_review(case["id"],_review(),_user(db,unauthorized),db)
            assert err.value.status_code in (403,404)
        with pytest.raises(HTTPException) as err:
            case_detail(case["id"],_user(db,3),db)
        assert err.value.status_code==404
        assert db.query(CaseTransition).filter_by(
            case_id=case["id"],action="SOURCE_REVIEW_RECORDED").count()==0

        record_source_review(case["id"],_review(),_user(db,2),db)
        route_case(case["id"],RouteCase(department="Hukum & Sengketa",
            target_scope="NATIONAL",assignee_id=1,
            note="Escalate to national officer for additional legal screening"),
            _user(db,2),db)
        after=case_detail(case["id"],_user(db,1),db)
        assert after["workflow_trace"]["steps"][1]["done"] is False
        assert after["can_record_source_review"] is False
        with pytest.raises(HTTPException) as err:
            record_source_review(case["id"],_review(),_user(db,2),db)
        assert err.value.status_code==403
    finally:
        db.close()


def test_negative_source_review_supersedes_previous_affirmative_review():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        record_source_review(case["id"],_review(),_user(db,2),db)
        assert case_detail(case["id"],_user(db,2),db)["workflow_trace"]["steps"][2]["done"]
        record_source_review(case["id"],_review(status="NEEDS_INFORMATION",opened=False,
            note="Further documents are needed and the original claim is not corroborated."),
            _user(db,2),db)
        trace=case_detail(case["id"],_user(db,2),db)["workflow_trace"]
        assert not trace["steps"][2]["done"]
        assert trace["latest_source_review_status"]=="NEEDS_INFORMATION"
    finally:
        db.close()


def test_missing_or_malformed_outcome_and_short_note_not_saved():
    db=dataset()
    try:
        case=_case(db)
        acknowledge_case(case["id"],_user(db,2),db)
        with pytest.raises(ValidationError):
            SourceReviewAction(status="SOURCE_CHECKED",note="Too short",original_source_opened=True)
        with pytest.raises(HTTPException) as err:
            record_source_review(case["id"],_review(status="LEGAL_VERDICT"),
                                 _user(db,2),db)
        assert err.value.status_code==422
        assert db.query(CaseTransition).filter_by(
            case_id=case["id"],action="SOURCE_REVIEW_RECORDED").count()==0
    finally:
        db.close()
