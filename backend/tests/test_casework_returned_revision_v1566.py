"""v156.6 returned report revision audit preservation; isolated SQLite only."""
import pytest
from fastapi import HTTPException
from app.casework import (CaseAssignment,CaseReport,CaseTransition,ReportDraft,
    ReportAction,update_report,transition_report)
from app.models import User
from test_casework_workflow import dataset

def setup_case(db):
    case=CaseAssignment(title="UAT revision",source_type="SOCIAL",source_id="11",
        campaign_id=90,source_url="https://example.test/post/11",
        source_excerpt="Sample",target_department="Pengawasan",
        originating_scope="NATIONAL",target_scope="NATIONAL",
        status="IN_REVIEW",created_by=1,assignee_id=1)
    db.add(case);db.flush()
    report=CaseReport(case_id=case.id,title="Returned UAT report",
        executive_summary="Initial summary",findings="Unverified allegations",
        verification_notes="Source accessible; facts unverified",
        recommendations="More verification needed",
        source_snapshot_json='{"source_id":"11"}',status="RETURNED",
        created_by=1,reviewed_by=4,
        review_comment="More independent context needed")
    db.add(report);db.commit()
    return case,report

def draft():
    return ReportDraft(title="UAT report revised",
        executive_summary="Clarified allegation versus facts",
        findings="Political opinion and unverified allegations",
        verification_notes="Independent supporting evidence is not yet available",
        recommendations="Seek reliable sources before legal evaluation")

def test_returned_report_is_archived_when_new_draft_saved():
    db=dataset()
    try:
        case,original=setup_case(db)
        revised=update_report(original.id,draft(),db.get(User,1),db)
        db.flush()
        assert revised["id"]!=original.id and revised["status"]=="DRAFT"
        assert revised["reviewed_by"] is None and revised["review_comment"]==""
        retained=db.get(CaseReport,original.id)
        saved=db.get(CaseReport,revised["id"])
        assert retained.status=="RETURNED"
        assert retained.reviewed_by==4
        assert retained.review_comment=="More independent context needed"
        assert retained.executive_summary=="Initial summary"
        assert saved.source_snapshot_json==retained.source_snapshot_json
        events=db.query(CaseTransition).filter_by(case_id=case.id,
            action="REPORT_REVISION_DRAFTED").all()
        assert len(events)==1
        assert str(original.id) in events[0].details_json
        assert str(saved.id) in events[0].details_json
        assert db.query(CaseReport).filter_by(case_id=case.id).count()==2
    finally:db.close()

def test_returned_report_requires_saved_revision_before_resubmission():
    db=dataset()
    try:
        _,original=setup_case(db)
        with pytest.raises(HTTPException) as err:
            transition_report(original.id,ReportAction(status="SUBMITTED"),
                              db.get(User,1),db)
        assert err.value.status_code==403
    finally:db.close()

def test_new_revision_can_be_submitted_and_preserves_returned_report():
    db=dataset()
    try:
        case,original=setup_case(db)
        new=update_report(original.id,draft(),db.get(User,1),db)
        submitted=transition_report(new["id"],ReportAction(status="SUBMITTED"),
                                    db.get(User,1),db)
        assert submitted["status"]=="SUBMITTED"
        assert db.get(CaseReport,original.id).status=="RETURNED"
        assert db.query(CaseTransition).filter_by(case_id=case.id,
            action="REPORT_SUBMITTED").count()==1
    finally:db.close()

def test_archived_returned_version_cannot_be_edited_again():
    db=dataset()
    try:
        _,original=setup_case(db)
        update_report(original.id,draft(),db.get(User,1),db)
        with pytest.raises(HTTPException) as err:
            update_report(original.id,draft(),db.get(User,1),db)
        assert err.value.status_code==409
    finally:db.close()

def test_unrelated_officer_cannot_create_new_revision():
    db=dataset()
    try:
        _,original=setup_case(db)
        with pytest.raises(HTTPException) as err:
            update_report(original.id,draft(),db.get(User,3),db)
        assert err.value.status_code==403
        assert db.query(CaseReport).count()==1
    finally:db.close()
