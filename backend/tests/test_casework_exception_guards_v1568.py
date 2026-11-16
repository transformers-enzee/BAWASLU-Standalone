"""Read-only SQLite regressions for BAWASLU negative casework permissions and sources."""
import pytest
from fastapi import HTTPException
from app.casework import (CaseAssignment,CaseReport,CaseTransition,ReportAction,
 SourceReviewAction,NewCase,create_case,record_source_review,transition_report,
 _validate_route)
from app.models import User
from app.access import default_permissions
from test_casework_workflow import dataset,p

def case(db,url="https://example.test/post/11",scope="NATIONAL",province=""):
    item=CaseAssignment(title="UAT exception safeguards",
        source_type="SOCIAL",source_id="11",campaign_id=90,
        source_url=url,source_excerpt="Saved UAT source text",
        target_department="Pengawasan",originating_scope="NATIONAL",
        target_scope=scope,target_province=province,
        verified_province=province,
        created_by=1,assignee_id=1,status="IN_REVIEW")
    db.add(item);db.flush()
    return item

def review(db,item,user_id=1,status="SOURCE_CHECKED",opened=True):
    return record_source_review(item.id,SourceReviewAction(
        status=status,note="STAGING UAT checked the saved source link and context.",
        original_source_opened=opened),db.get(User,user_id),db)

@pytest.mark.parametrize("url",[
    "", "https://", "http://", "https:///post/11",
    "javascript:alert(1)", "https://someone:secret@example.test/post/11",
    "https://[bad-host", "https://@example.test/post/11"])
def test_invalid_original_urls_cannot_be_attested_as_checked(url):
    db=dataset()
    try:
        item=case(db,url)
        with pytest.raises(HTTPException) as err: review(db,item)
        assert err.value.status_code==422
        assert db.query(CaseTransition).filter_by(case_id=item.id).count()==0
    finally:db.close()

def test_valid_saved_link_and_explicit_attestation_succeed():
    db=dataset()
    try:
        item=case(db)
        result=review(db,item)
        assert result["status"]=="SOURCE_CHECKED"
        assert result["not_a_content_or_legal_verdict"] if "not_a_content_or_legal_verdict" in result else result["requires_separate_legal_assessment"]
        assert db.query(CaseTransition).filter_by(case_id=item.id,
            action="SOURCE_REVIEW_RECORDED").count()==1
    finally:db.close()

def test_unopened_valid_source_does_not_count_as_checked():
    db=dataset()
    try:
        item=case(db)
        with pytest.raises(HTTPException) as err:review(db,item,opened=False)
        assert err.value.status_code==422
        assert db.query(CaseTransition).filter_by(case_id=item.id).count()==0
    finally:db.close()

def test_unavailable_source_can_be_recorded_without_false_confirmation():
    db=dataset()
    try:
        item=case(db,url="")
        result=review(db,item,status="SOURCE_UNAVAILABLE",opened=False)
        assert result["status"]=="SOURCE_UNAVAILABLE"
        assert result["original_source_opened"] is False
        assert db.query(CaseTransition).filter_by(case_id=item.id).count()==1
    finally:db.close()

def test_different_officer_cannot_attest_assigned_source():
    db=dataset()
    try:
        item=case(db)
        with pytest.raises(HTTPException) as err:review(db,item,user_id=4)
        assert err.value.status_code==403
        assert db.query(CaseTransition).filter_by(case_id=item.id).count()==0
    finally:db.close()

def test_reviewer_without_human_validation_cannot_approve():
    db=dataset()
    try:
        item=case(db)
        report=CaseReport(case_id=item.id,title="UAT submitted",
            findings="Claims require corroboration",
            verification_notes="Source not independently verified",
            status="SUBMITTED",created_by=1)
        db.add(report);db.flush()
        with pytest.raises(HTTPException) as err:
            transition_report(report.id,ReportAction(status="APPROVED"),
                              db.get(User,2),db)
        assert err.value.status_code in (403,404)
        assert report.status=="SUBMITTED"
        assert db.query(CaseTransition).filter_by(case_id=item.id).count()==0
    finally:db.close()

def test_author_cannot_approve_own_report_even_with_permission():
    db=dataset()
    try:
        item=case(db)
        report=CaseReport(case_id=item.id,title="UAT submitted",
            findings="Claims require corroboration",
            verification_notes="Source not independently verified",
            status="SUBMITTED",created_by=1)
        db.add(report);db.flush()
        with pytest.raises(HTTPException) as err:
            transition_report(report.id,ReportAction(status="APPROVED"),
                              db.get(User,1),db)
        assert err.value.status_code==403
        assert report.status=="SUBMITTED"
    finally:db.close()

def test_unverified_province_never_authorizes_province_route():
    db=dataset()
    try:
        item=case(db,province="")
        with pytest.raises(HTTPException) as err:
            _validate_route(item,p(db,1),"PROVINCE","Riau")
        assert err.value.status_code==422
    finally:db.close()

def test_confirmed_province_does_not_authorize_different_province():
    db=dataset()
    try:
        item=case(db,province="Riau")
        with pytest.raises(HTTPException) as err:
            _validate_route(item,p(db,1),"PROVINCE","Bali")
        assert err.value.status_code==422
    finally:db.close()
