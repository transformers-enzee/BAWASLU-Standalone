"""Paid pilot requires explicit operator intent and restricted authorization."""
import pytest
from app.assessment_pilot import start_assessment_pilot


def test_paid_pilot_rejects_unauthorized_operator_before_db_work():
    with pytest.raises(PermissionError, match="National Administrator"):
        start_assessment_pilot(None, {"role": "Provincial Analyst"}, {
            "sample_size": 40, "confirm_ai_cost": True}, "12")


def test_paid_pilot_requires_cost_confirmation_before_db_work():
    with pytest.raises(ValueError, match="Explicit paid AI request confirmation"):
        start_assessment_pilot(None, {
            "role": "National Administrator", "status": "Active",
            "permissions": {"administration": True}}, {"sample_size": 40}, "12")


def test_targeted_pilot_never_auto_enqueues_other_posts():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1] / "app" / "auto_relevance.py").read_text()
    assert "CampaignEvidence.result_id==int(target_result_id)" in source
    assert "(requested_limit is None or target_result_id is not None) and not reserve_automatic_ai_request" in source
    assert "job.state='FAILED' if target_result_id is not None" in source


def test_paid_route_dispatches_only_authorized_selected_ids():
    from pathlib import Path
    main=(Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
    pilot=(Path(__file__).resolve().parents[1] / "app" / "assessment_pilot.py").read_text()
    assert "body.action=='campaignAssessmentPilotStart' and result.get('started')" in main
    assert "background_tasks.add_task(execute_assessment_pilot" in main
    assert "payload.get('confirm_ai_cost') is not True" in pilot
    assert "if not str(campaign.description or '').strip()" in pilot
