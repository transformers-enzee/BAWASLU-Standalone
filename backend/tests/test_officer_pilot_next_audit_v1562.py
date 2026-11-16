"""Next audit-stage triage, never official acceptance. All SQLite fixtures."""
from app.casework import pilot_intake, CaseAssignment, CaseTransition
from app.models import User, CampaignEvidence
from app.officer_pilot_audit import observed_casework_stages
from test_casework_workflow import dataset
from test_officer_pilot_intake_v1544 import finding, post, _patch
from test_officer_pilot_active_case_lookup_v1547 import _case

def _run(monkeypatch,db):
    _patch(monkeypatch,[finding(posts=[post()])])
    return pilot_intake(db.get(User,1),db)

def test_next_missing_stage_comes_from_authorized_case_audit(monkeypatch):
    db=dataset()
    try:
        case=_case(11);case.source_url="https://example.test/post/11"
        db.add(case);db.flush()
        db.add(CaseTransition(case_id=case.id,actor_id=1,action="CREATED",details_json="{}"))
        db.commit()
        res=_run(monkeypatch,db);row=res["items"][0]
        assert row["acceptance_next_audit_action_status"]=="NEXT_UNOBSERVED_STAGE_IN_AVAILABLE_AUDIT"
        assert row["acceptance_next_audit_stage"]=="receiving_officer_accepted"
        assert row["acceptance_audit_observed_stage_count"]==1
        assert res["acceptance_preview_next_missing_stage_count"]==1
        assert row["acceptance_formal_signoff_still_required"] is True
        assert all(not x["completed"] for x in row["acceptance_workflow_checklist"])
    finally:db.close()

def test_bounded_200_event_history_does_not_claim_next_missing_stage(monkeypatch):
    db=dataset()
    try:
        case=_case(11);case.source_url="https://example.test/post/11"
        db.add(case);db.flush()
        for _ in range(200):
            db.add(CaseTransition(case_id=case.id,actor_id=1,action="NOTE",details_json="{}"))
        db.commit()
        res=_run(monkeypatch,db);row=res["items"][0]
        assert row["acceptance_audit_window_limited"] is True
        assert row["acceptance_next_audit_action_status"]=="HISTORY_INCOMPLETE_REVIEW_FULL_AUDIT"
        assert row["acceptance_next_audit_stage"] is None
        assert row["acceptance_missing_audit_evidence_not_confirmed_absent"] is True
        assert res["acceptance_preview_incomplete_audit_count"]==1
        assert res["acceptance_preview_next_missing_stage_count"]==0
        assert all(not x["completed"] for x in row["acceptance_workflow_checklist"])
    finally:db.close()

def test_no_case_means_no_case_audit_stage_recommendation(monkeypatch):
    db=dataset()
    try:
        row=_run(monkeypatch,db)["items"][0]
        assert row["acceptance_next_audit_stage"] is None
        assert row["acceptance_next_audit_action_status"]=="NO_VISIBLE_CASE_AUDIT_AVAILABLE"
    finally:db.close()

def test_unlinked_source_does_not_leak_case_stage(monkeypatch):
    db=dataset()
    try:
        case=_case(11);case.source_url="https://example.test/post/11"
        db.add(case);db.flush()
        db.add(CaseTransition(case_id=case.id,actor_id=1,action="CREATED",details_json="{}"))
        db.commit()
        db.query(CampaignEvidence).filter_by(campaign_id=90,result_id=11).delete()
        db.commit()
        row=_run(monkeypatch,db)["items"][0]
        assert row["pilot_next_action"]=="SOURCE_UNAVAILABLE"
        assert row["acceptance_next_audit_action_status"]=="NO_VISIBLE_CASE_AUDIT_AVAILABLE"
        assert row["acceptance_next_audit_stage"] is None
        assert row["acceptance_case_audit_evidence_available"] is False
    finally:db.close()

def test_per_case_audit_boundary_not_entire_cohort():
    db=dataset()
    try:
        first=_case(11);first.source_url="https://example.test/post/11"
        other=_case(12);other.source_url="https://example.test/post/12"
        db.add_all([first,other]);db.flush()
        for _ in range(200):
            db.add(CaseTransition(case_id=first.id,actor_id=1,action="NOTE",details_json="{}"))
        db.add(CaseTransition(case_id=other.id,actor_id=1,action="CREATED",details_json="{}"))
        db.commit()
        values=observed_casework_stages(db,[first,other])
        assert values[first.id]["next_stage_evidence_status"]=="HISTORY_INCOMPLETE_REVIEW_FULL_AUDIT"
        assert values[first.id]["next_unobserved_stage"] is None
        assert values[other.id]["next_stage_evidence_status"]=="NEXT_UNOBSERVED_STAGE_IN_AVAILABLE_AUDIT"
        assert values[other.id]["next_unobserved_stage"]=="receiving_officer_accepted"
    finally:db.close()
