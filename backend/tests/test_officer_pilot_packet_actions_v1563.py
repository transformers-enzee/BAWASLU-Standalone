"""v156.3: reviewer triage is period-scoped and never grants acceptance."""
import csv
import io
from app.officer_pilot_readiness import officer_pilot_readiness, officer_pilot_case_rows
from app.casework import CaseTransition
from app.management_reporting import officer_pilot_csv
from app.models import User
from test_casework_workflow import dataset
from test_management_briefings_v1468 import dataset as management_dataset

def test_no_casework_never_claims_accepted_or_missing():
    result=officer_pilot_readiness([],{},[])
    assert result["authorized_case_count"]==0
    assert all(n==0 for n in result["reviewer_action_counts"].values())
    assert result["pilot_packet_review_status"]=="HUMAN_ACCEPTANCE_PENDING"
    assert result["missing_stages_are_window_observations_not_confirmed_absence"] is True

def test_existing_case_without_events_requires_full_history_review():
    db=dataset()
    try:
        from test_officer_pilot_active_case_lookup_v1547 import _case
        case=_case(11);db.add(case);db.commit()
        row=officer_pilot_case_rows([case],{},[])[0]
        assert row["recommended_reviewer_action"]=="VERIFY_UNOBSERVED_STAGES_AGAINST_FULL_CASE_HISTORY"
        assert row["next_unobserved_step"]=="source_linked"
        assert row["missing_stage_confirmed_absent"] is False
        assert row["full_case_lifetime_audit_reviewed"] is False
        assert row["formal_human_acceptance_pending"] is True
    finally:db.close()

def test_two_hundred_event_window_never_diagnoses_missing_stage():
    db=dataset()
    try:
        from test_officer_pilot_active_case_lookup_v1547 import _case
        case=_case(11);db.add(case);db.flush()
        events=[CaseTransition(case_id=case.id,actor_id=1,action="NOTE",
                               details_json="{}") for _ in range(200)]
        db.add_all(events)
        db.flush()
        result=officer_pilot_readiness([case],{},events)
        row=result["case_preview"][0]
        assert row["audit_event_window_limited"] is True
        assert row["recommended_reviewer_action"]=="INSPECT_TRUNCATED_WINDOW_AND_FULL_CASE_HISTORY"
        assert result["reviewer_action_counts"]["INSPECT_TRUNCATED_WINDOW_AND_FULL_CASE_HISTORY"]==1
        assert row["missing_stage_confirmed_absent"] is False
    finally:db.close()

def test_case_created_audit_is_observation_not_acceptance():
    db=dataset()
    try:
        from test_officer_pilot_active_case_lookup_v1547 import _case
        case=_case(11);case.source_url="https://example.test/post/11";db.add(case);db.flush()
        event=CaseTransition(case_id=case.id,actor_id=1,action="CREATED",details_json="{}")
        result=officer_pilot_readiness([case],{},[event])
        assert result["stage_counts"]["source_linked"]==1
        assert result["reviewer_action_counts"]["VERIFY_UNOBSERVED_STAGES_AGAINST_FULL_CASE_HISTORY"]==1
        assert result["authorized_human_signoff_received"] is False
    finally:db.close()
