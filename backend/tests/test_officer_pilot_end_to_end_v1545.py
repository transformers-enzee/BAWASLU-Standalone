"""v154.5: officer-led pilot intake, usable evidence selection and idempotent case creation.

All data in these regression tests is isolated in-memory SQLite. The tests
never create actual assignments in the connected Supabase database.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import event
from app.officer_pilot_intake import officer_pilot_candidates
from app.casework import (
    CaseAssignment,CaseTransition,CaseReport,NewCase,ReportAction,
    acknowledge_case,case_detail,create_case,create_report,record_source_review,
    transition_report, pilot_intake
)
from app.models import User,EvidenceAssessment
from app.access import profile
from app.officer_pilot_readiness import officer_pilot_readiness
from app.management_reporting import build_briefing
from test_casework_workflow import dataset,confirmed
from test_officer_acceptance_v1480 import _review,_report
from test_officer_pilot_intake_v1544 import post,finding

def user(db,ident=1):
    return db.get(User,ident)

def request(db,ident=1,**updates):
    values=dict(source_type="SOCIAL",source_id="11",campaign_id=90,
        department="Pengawasan",target_scope="NATIONAL",
        title="Original officer-authored casework")
    values.update(updates)
    return create_case(NewCase(**values),user(db,ident),db)

def candidate(*findings,limit=12):
    return officer_pilot_candidates(findings,limit=limit)

def test_complete_authorized_campaign_preferred_to_incomplete_flagged_version():
    flagged=finding("source_review",[post(11,90,url="")])
    usable=finding("discussion",[post(11,91,url="https://example.invalid/p/11")])
    x=candidate(flagged,usable)
    row=x["items"][0]
    assert row["campaign_id"]=="91"
    assert row["review_signal"]=="SAVED_PUBLIC_CONCERN_DISCUSSION"
    assert row["casework_link"].endswith("source_id=11&campaign_id=91&tab=assignments")
    assert x["selection_basis"]=="USABLE_SOURCE_FIRST_THEN_SAVED_REVIEW_SIGNAL"
    assert x["source_prefill_available_count"]==1
    assert x["source_recovery_required_count"]==0

def test_strongest_saved_flag_wins_when_both_campaign_versions_are_actionable():
    a=finding("discussion",[post(11,91)])
    b=finding("source_review",[post(11,90)])
    first=candidate(a,b)
    second=candidate(b,a)
    assert first["items"]==second["items"]
    assert first["items"][0]["campaign_id"]=="90"
    assert first["items"][0]["review_signal"]=="SAVED_SOURCE_FLAG_REVIEW"

def test_same_incomplete_source_multiple_campaigns_is_counted_once():
    a=finding("source_review",[post(11,90,url="")])
    b=finding("discussion",[post(11,91,text="")])
    x=candidate(a,b)
    assert x["observed_authorized_unique_sources"]==1
    assert x["source_prefill_available_count"]==0
    assert x["source_recovery_required_count"]==1
    assert x["items"][0]["casework_link"] is None

def test_available_and_recovery_counts_cover_full_authorized_cohort():
    findings=[finding("source_awareness",[
        post(i,90,url="https://example.invalid/p/"+str(i) if i%2 else "")
    ]) for i in range(1,21)]
    x=candidate(*findings)
    assert len(x["items"])==12
    assert x["observed_authorized_unique_sources"]==20
    assert x["source_prefill_available_count"]==10
    assert x["source_recovery_required_count"]==10
    assert x["preview_is_sample"] is True

def test_missing_original_url_never_looks_ready_even_with_high_review_signal():
    x=candidate(finding("source_review",[post(url="javascript:alert(1)")]))
    assert x["items"][0]["review_signal"]=="SAVED_SOURCE_FLAG_REVIEW"
    assert x["items"][0]["original_source_url_available"] is False
    assert x["source_prefill_available_count"]==0
    assert x["items"][0]["casework_link"] is None

def test_same_officer_second_save_reuses_active_case_and_no_duplicate_event():
    db=dataset()
    try:
        first=request(db)
        assert first["existing"] is False
        assert first["assignment_created"] is True
        before=db.query(CaseTransition).count()
        second=request(db)
        assert second["id"]==first["id"]
        assert second["existing"] is True
        assert second["assignment_created"] is False
        assert db.query(CaseAssignment).count()==1
        assert db.query(CaseTransition).count()==before==1
    finally:db.close()

def test_duplicate_request_cannot_overwrite_title_notes_department_or_ownership():
    db=dataset()
    try:
        first=request(db,title="Validated by the initiating officer",
                      notes="Original note is retained")
        second=request(db,title="Untrusted replacement title",
                       department="Data & Analisis",
                       notes="Unexpected overwrite")
        stored=db.get(CaseAssignment,first["id"])
        assert second["existing"] is True
        assert stored.title=="Validated by the initiating officer"
        assert stored.notes=="Original note is retained"
        assert stored.target_department=="Pengawasan"
        assert second["title"]==stored.title
        assert stored.created_by==1
    finally:db.close()

def test_another_authorized_national_officer_sees_existing_case_not_new_one():
    db=dataset()
    try:
        first=request(db,ident=1)
        second=request(db,ident=4)
        assert first["id"]==second["id"]
        assert second["existing"] is True
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_closed_case_can_be_reopened_as_new_casework_without_mutating_history():
    db=dataset()
    try:
        first=request(db)
        old=db.get(CaseAssignment,first["id"])
        old.status="CLOSED"
        db.commit()
        second=request(db)
        assert second["id"]!=first["id"]
        assert second["existing"] is False
        assert db.get(CaseAssignment,first["id"]).status=="CLOSED"
        assert db.query(CaseAssignment).count()==2
        assert db.query(CaseTransition).count()==2
    finally:db.close()

def test_invalid_department_rejected_even_when_an_active_case_exists():
    db=dataset()
    try:
        request(db)
        with pytest.raises(HTTPException) as exc:
            request(db,department="Unauthorized team")
        assert exc.value.status_code==422
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_unverified_province_does_not_gain_permission_via_duplicate_reuse():
    db=dataset()
    try:
        request(db)
        with pytest.raises(HTTPException) as exc:
            request(db,target_scope="PROVINCE",target_province="Riau")
        assert exc.value.status_code==422
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_changed_source_relevance_blocks_second_save_before_existing_case_lookup():
    db=dataset()
    try:
        first=request(db)
        assessment=db.query(EvidenceAssessment).filter_by(campaign_id=90,result_id=11).first()
        assessment.relevance_label="IRRELEVANT"
        db.commit()
        with pytest.raises(HTTPException) as exc:
            request(db)
        assert exc.value.status_code==422
        assert db.query(CaseAssignment).count()==1
        assert db.get(CaseAssignment,first["id"]).status=="OPEN"
    finally:db.close()

def test_forged_social_source_remains_forbidden_even_if_other_case_exists():
    db=dataset()
    try:
        request(db)
        with pytest.raises(HTTPException) as exc:
            request(db,source_id="999999")
        assert exc.value.status_code in (403,422)
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_bali_role_cannot_learn_riau_case_id_by_repeating_save():
    db=dataset()
    try:
        request(db)
        with pytest.raises(HTTPException) as exc:
            request(db,ident=3)
        assert exc.value.status_code in (403,422)
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_riau_role_cannot_obtain_hidden_national_case_id_on_save():
    db=dataset()
    try:
        first=request(db)
        try:
            second=request(db,ident=2)
        except HTTPException as exc:
            # If this role cannot create a national assignment, it must
            # reject without disclosing the national case identifier.
            assert exc.status_code in (403,422)
        else:
            assert second["id"]!=first["id"]
            assert second["existing"] is False
            assert second["created_by"]==2
    finally:db.close()

def test_new_case_has_no_automatic_human_approval_or_report():
    db=dataset()
    try:
        new=request(db)
        assert new["status"]=="OPEN"
        assert new["assignment_created"] is True
        assert db.query(CaseReport).count()==0
        events=db.query(CaseTransition).all()
        assert [event.action for event in events]==["CREATED"]
    finally:db.close()

def test_duplicated_save_never_invokes_ai_or_creates_report_or_review():
    db=dataset()
    try:
        request(db)
        second=request(db)
        assert second["assignment_created"] is False
        assert db.query(CaseReport).count()==0
        assert db.query(CaseTransition).filter(
            CaseTransition.action.like("REPORT_%")).count()==0
    finally:db.close()

def test_workflow_from_confirmed_saved_social_source_through_independent_review():
    db=dataset()
    try:
        confirmed(db)
        created=request(db,ident=1,department="Penanganan Pelanggaran",
            target_scope="PROVINCE",target_province="Riau",assignee_id=2)
        assert created["existing"] is False
        assert created["target_province"]=="Riau"
        repeated=request(db,ident=1,department="Penanganan Pelanggaran",
            target_scope="PROVINCE",target_province="Riau",assignee_id=2)
        assert repeated["id"]==created["id"]
        assert repeated["existing"] is True
        acknowledged=acknowledge_case(created["id"],user(db,2),db)
        assert acknowledged["status"]=="IN_REVIEW"
        reviewed=record_source_review(created["id"],_review(),user(db,2),db)
        assert reviewed["requires_separate_legal_assessment"] is True
        officer_report=create_report(created["id"],_report(),user(db,2),db)
        submitted=transition_report(officer_report["id"],
                ReportAction(status="SUBMITTED"),user(db,2),db)
        assert submitted["status"]=="SUBMITTED"
        with pytest.raises(HTTPException) as exc:
            transition_report(officer_report["id"],
                ReportAction(status="APPROVED"),user(db,2),db)
        assert exc.value.status_code==403
        approved=transition_report(officer_report["id"],
                ReportAction(status="APPROVED"),user(db,1),db)
        assert approved["status"]=="APPROVED"
        details=case_detail(created["id"],user(db,2),db)
        assert details["workflow_trace"]["completed"]==5
        latest={created["id"]:db.get(CaseReport,officer_report["id"])}
        pilot=officer_pilot_readiness(
            [db.get(CaseAssignment,created["id"])],latest,
            db.query(CaseTransition).order_by(CaseTransition.id).all())
        assert pilot["five_stage_observed_case_count"]==1
        assert pilot["authorized_human_signoff_received"] is False
        assert pilot["source_authenticity_verified"] is False
        snap=build_briefing(db,profile(db,user(db,1)),1,language="en")
        assert snap["template"]["approval_state"]=="DRAFT_NOT_APPROVED"
    finally:db.close()

def test_partial_source_review_does_not_count_as_complete_pilot():
    db=dataset()
    try:
        c=request(db)
        assert c["assignment_created"] is True
        trace=case_detail(c["id"],user(db,1),db)["workflow_trace"]
        assert trace["completed"]==1
        assert trace["legal_violation_determined"] is False
    finally:db.close()

def test_no_source_readiness_can_create_cases_without_officer_request():
    data=candidate(finding("source_review",[post()]))
    assert data["no_assignment_created"] is True
    assert data["original_source_truth_not_verified"] is True
    assert data["no_paid_provider_called"] is True

def test_preview_has_no_automatic_assignment_or_human_signoff():
    data=candidate(finding("source_awareness",[post()]))
    assert data["no_assignment_created"] is True
    assert data["requires_officer_confirmation"] is True
    assert data["items"][0]["automatic_assignment_created"] is False
    assert data["items"][0]["legal_violation_confirmed"] is False

def test_real_inbox_reader_feeds_pilot_without_test_shortcuts():
    """Exercise campaign evidence -> saved Inbox -> shortlist -> casework."""
    db=dataset()
    try:
        from app.inbox_read_cache import invalidate
        invalidate()
        result=pilot_intake(user(db,1),db)
        assert result["schema"]=="BAWASLU_OFFICER_PILOT_INTAKE_V1544"
        assert result["no_assignment_created"] is True
        assert result["requires_officer_confirmation"] is True
        assert db.query(CaseAssignment).count()==0
        assert result["observed_authorized_unique_sources"]>=1
        assert any(x["source_id"]=="11" and x["campaign_id"]=="90"
                   for x in result["items"])
        reviewed=next(x for x in result["items"] if x["source_id"]=="11")
        assert reviewed["casework_link"].startswith("/inbox?casework=1")
        created=request(db)
        assert created["assignment_created"] is True
        invalidate()
        later=pilot_intake(user(db,1),db)
        matching=next(x for x in later["items"] if x["source_id"]=="11")
        assert matching["case_already_exists_in_visible_scope"] is True
        assert matching["visible_open_case_id"]==created["id"]
    finally:
        db.close()

