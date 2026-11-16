"""v158.7 acceptance prep must not impersonate external human sign-off."""
import json
import pytest
from fastapi import HTTPException,Response
from app.assistant_acceptance_readiness import build_acceptance_readiness
from app.assistant_human_review import build_human_review_packet
from app.assistant_eval_sampling import build_evaluation_question_plan,acceptance_readiness
from app.assistant_legal_benchmark import run_legal_signal_benchmark
from test_assistant_eval_sampling_v1488 import findings
from app.models import User
from test_management_briefings_v1468 import dataset

def test_acceptance_readiness_is_honest_and_metadata_only():
    packet=build_human_review_packet(build_evaluation_question_plan(findings(35),24))
    result=build_acceptance_readiness(packet,run_legal_signal_benchmark())
    assert result["status"]=="PREPARATION_ONLY_NOT_FORMAL_ACCEPTANCE"
    assert result["prepared_questions"]==24 and result["sample_shortfall"]==0
    assert result["negative_control_prepared"] is True
    assert result["synthetic_benchmark_is_real_model_accuracy"] is False
    assert result["human_accuracy_measured"] is False
    assert result["formal_client_acceptance_complete"] is False
    assert result["legal_reference_signoff_complete"] is False
    assert result["real_model_answers_reviewed"]==0
    assert result["gaps_remaining"]==5
    assert "PRIVATE_RAW_MESSAGE_SHOULD_NOT_APPEAR" not in json.dumps(result)
    assert "source_url" not in json.dumps(result)
    assert result["database_writes"]==0 and result["paid_ai_calls"]==0

def test_shortfall_is_visible_not_fabricated():
    packet=build_human_review_packet(build_evaluation_question_plan(findings(1),24))
    result=build_acceptance_readiness(packet,run_legal_signal_benchmark())
    assert result["sample_shortfall"]==23
    assert result["gaps_remaining"]==6
    assert result["readiness_gaps"][0]["track"]=="EVALUATION_SAMPLE_SHORTFALL"

def test_empty_packet_has_explicit_sample_shortfall():
    packet=build_human_review_packet(build_evaluation_question_plan([],24))
    result=build_acceptance_readiness(packet,run_legal_signal_benchmark())
    assert result["prepared_questions"]==0
    assert result["sample_shortfall"]==24
    assert not result["covered_categories"]

def test_rejects_invalid_input():
    with pytest.raises(ValueError):
        build_acceptance_readiness({},{"number_of_cases":1})
    with pytest.raises(ValueError):
        build_acceptance_readiness({"review_items":[]},None)

def test_admin_only_endpoint(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
            lambda conn,p:(findings(4),{}))
        monkeypatch.setattr(assistant_eval_sampling,"profile",lambda conn,user:{
            "role":"National Administrator",
            "status":"Active",
            "permissions":{"administration":True,"view_intelligence":True}})
        response=Response()
        result=acceptance_readiness(response,target=24,user=db.get(User,1),db=db)
        assert result["sample_shortfall"]==20
        assert response.headers["Cache-Control"]=="private, no-store"
        assert response.headers["X-Evaluation-Generation"]=="NONE"
        monkeypatch.setattr(assistant_eval_sampling,"profile",lambda conn,user:{
            "status":"Active","permissions":{"view_intelligence":True,
                                               "administration":False}})
        with pytest.raises(HTTPException) as e:
            acceptance_readiness(Response(),target=24,user=db.get(User,2),db=db)
        assert e.value.status_code==403
    finally:db.close()
