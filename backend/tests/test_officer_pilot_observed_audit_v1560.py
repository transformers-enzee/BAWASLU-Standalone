"""Real case audit observations in read-only officer shortlist, no live writes."""
import json
from app.casework import pilot_intake, CaseAssignment, CaseTransition
from app.models import User, CampaignEvidence
from test_casework_workflow import dataset
from test_officer_pilot_intake_v1544 import finding, post, _patch
from test_officer_pilot_active_case_lookup_v1547 import _case

def _run(monkeypatch,db):
    _patch(monkeypatch,[finding(posts=[post()])])
    return pilot_intake(db.get(User,1),db)

def test_existing_case_stage_observed_only_from_real_audit_event(monkeypatch):
    db=dataset()
    try:
        case=_case(11);db.add(case);db.flush()
        db.add(CaseTransition(case_id=case.id,actor_id=1,action="CREATED",
                              details_json="{}"))
        db.commit()
        result=_run(monkeypatch,db)
        item=result["items"][0]
        steps={step["key"]:step for step in item["acceptance_workflow_checklist"]}
        assert steps["source_linked"]["audit_observed"] is True
        assert steps["source_linked"]["completed"] is False
        assert steps["receiving_officer_accepted"]["audit_observed"] is False
        assert item["acceptance_audit_observed_stage_count"]==1
        assert item["acceptance_case_audit_evidence_available"] is True
        assert item["acceptance_casework_audit_is_not_formal_acceptance"] is True
        assert result["acceptance_audit_evidence_is_not_human_signoff"] is True
        assert db.query(CaseTransition).count()==1
    finally:db.close()

def test_case_without_events_never_marks_stage_completed(monkeypatch):
    db=dataset()
    try:
        db.add(_case(11));db.commit()
        item=_run(monkeypatch,db)["items"][0]
        assert item["acceptance_case_audit_evidence_available"] is True
        assert item["acceptance_audit_observed_stage_count"]==0
        assert all(not step["audit_observed"] and not step["completed"]
                   for step in item["acceptance_workflow_checklist"])
    finally:db.close()

def test_source_without_case_has_no_audit_trace(monkeypatch):
    db=dataset()
    try:
        item=_run(monkeypatch,db)["items"][0]
        assert item["acceptance_case_audit_evidence_available"] is False
        assert item["acceptance_audit_observed_stage_count"]==0
        assert all(step["status"]=="REQUIRES_AUTHORIZED_CASEWORK_VERIFICATION"
                   for step in item["acceptance_workflow_checklist"])
    finally:db.close()

def test_unlinked_source_does_not_expose_prior_case_audit(monkeypatch):
    db=dataset()
    try:
        case=_case(11);db.add(case);db.flush()
        db.add(CaseTransition(case_id=case.id,actor_id=1,action="CREATED",
                              details_json="{}"))
        db.commit()
        db.query(CampaignEvidence).filter_by(campaign_id=90,result_id=11).delete()
        db.commit()
        item=_run(monkeypatch,db)["items"][0]
        assert item["pilot_next_action"]=="SOURCE_UNAVAILABLE"
        assert item["acceptance_saved_source_reference"]["visible_case_id"] is None
        assert item["acceptance_case_audit_evidence_available"] is False
        assert not any(step["audit_observed"] for step in item["acceptance_workflow_checklist"])
    finally:db.close()

def test_two_cases_have_independent_per_case_event_windows():
    from app.officer_pilot_audit import observed_casework_stages
    db=dataset()
    try:
        first=_case(11);second=_case(12)
        db.add_all([first,second]);db.flush()
        for i in range(200):
            db.add(CaseTransition(case_id=first.id,actor_id=1,action="NOTE",
                                  details_json="{}"))
        db.add(CaseTransition(case_id=second.id,actor_id=1,action="CREATED",
                              details_json="{}"))
        db.commit()
        out=observed_casework_stages(db,[first,second])
        assert out[first.id]["audit_event_window_limited"] is True
        assert out[second.id]["observed_stages"]["source_linked"] is True
        assert out[second.id]["audit_event_window_limited"] is False
    finally:db.close()
