"""v158.6: reviewer packets do not conflate synthetic checks with human approval."""
import json
import pytest
from fastapi import HTTPException,Response
from app.assistant_human_review import build_human_review_packet,REVIEW_DIMENSIONS
from app.assistant_eval_sampling import build_evaluation_question_plan,human_review_packet
from test_assistant_eval_sampling_v1488 import findings
from app.models import User
from test_management_briefings_v1468 import dataset

def test_packet_has_unscored_rubric_and_negative_control():
    plan=build_evaluation_question_plan(findings(35),24)
    packet=build_human_review_packet(plan)
    assert packet["prepared_questions"]==24
    assert packet["human_reviews_completed"]==0
    assert packet["evaluated_answers"]==0
    assert packet["human_accuracy_measured"] is False
    assert packet["legal_signoff_complete"] is False
    assert packet["formal_client_acceptance_complete"] is False
    assert packet["model_answers_generated"] is False
    assert packet["paid_ai_calls"]==0 and packet["database_writes"]==0
    assert packet["negative_control"]["source_record_id"]=="SOCIAL-0"
    assert len(packet["review_items"])==24
    assert all(len(item["review_dimensions"])==len(REVIEW_DIMENSIONS) for item in packet["review_items"])
    assert all(all(d["rating"] is None for d in item["review_dimensions"])
               for item in packet["review_items"])
    assert all(not item["answer_generated"] and not item["human_review_completed"]
               for item in packet["review_items"])
    assert "PRIVATE_RAW_MESSAGE_SHOULD_NOT_APPEAR" not in json.dumps(packet)

def test_empty_plan_does_not_misrepresent_review_completion():
    packet=build_human_review_packet(build_evaluation_question_plan([],24))
    assert packet["prepared_questions"]==0
    assert packet["shortfall"]==24
    assert packet["review_items"]==[]
    assert packet["status"]=="AWAITING_INDEPENDENT_HUMAN_REVIEW"

def test_invalid_plan_rejected():
    with pytest.raises(ValueError):
        build_human_review_packet({})
    with pytest.raises(ValueError):
        build_human_review_packet(None)

def test_permission_scoped_endpoint(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",lambda conn,p:(findings(4),{}))
        monkeypatch.setattr(assistant_eval_sampling,"profile",lambda conn,user:{
            "status":"Active","permissions":{"view_intelligence":True},"province":"Riau"})
        response=Response()
        packet=human_review_packet(response,target=24,user=db.get(User,2),db=db)
        assert packet["prepared_questions"]==4
        assert response.headers["Cache-Control"]=="private, no-store"
        assert response.headers["X-Evaluation-Generation"]=="NONE"
        monkeypatch.setattr(assistant_eval_sampling,"profile",lambda conn,user:{
            "status":"Active","permissions":{"view_intelligence":False}})
        with pytest.raises(HTTPException) as err:
            human_review_packet(Response(),target=24,user=db.get(User,2),db=db)
        assert err.value.status_code==403
    finally:db.close()
