"""Redacted human worksheet from authorized historical Assistant audits."""
import json
import pytest
from app.assistant_saved_reply_human_packet import build_authorized_saved_reply_review_packet as build


def row(status="AUDITED", triage=None):
    output={"thread_id":"123e4567-e89b-12d3-a456-426614174000",
            "answer_message_index":3,"status":status}
    if status=="AUDITED":
        output["response_quality_triage"]=triage or {
            "status":"REVIEW_FLAGS_PRESENT",
            "diagnostics_complete":True,
            "human_review_route":"REVIEW_FLAGGED_SOURCE_CLAIMS",
        }
    return output


def batch(items):
    return {"selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
            "requested":len(items),"results":items}


def test_packet_is_blank_redacted_and_requires_human_review():
    input_batch=batch([row(),row("SOURCE_UNAVAILABLE")])
    input_batch["original_answer"]="SECRET ANSWER DO NOT EXPORT"
    report=build(input_batch)
    assert report["review_ready_replies"]==1
    assert report["ineligible_or_unavailable_replies"]==1
    assert report["human_review_completed"] is False
    assert report["actual_model_accuracy_measured"] is False
    assert report["generation_calls"]==0
    assert report["database_writes"]==0
    assert len(report["items"][0]["review_dimensions"])==6
    assert all(x["rating"] is None and x["reviewer_note"] is None
               for x in report["items"][0]["review_dimensions"])
    assert report["items"][0]["source_access_recheck_required_at_review_time"] is True
    assert "SECRET ANSWER" not in json.dumps(report)


def test_incomplete_qa_produces_no_automatic_officer_rating():
    report=build(batch([row(triage={
        "status":"INCOMPLETE_DIAGNOSTICS",
        "diagnostics_complete":False,
        "human_review_route":"REPEAT_INCOMPLETE_QA",
    })]))
    task=report["items"][0]
    assert task["recommended_action"]=="REPEAT_INCOMPLETE_QA"
    assert task["diagnostics_complete"] is False
    assert task["review_completed"] is False


@pytest.mark.parametrize("wrong",[
    {"selection_method":"AUTO_SELECTED","requested":1,"results":[row()]},
    {"selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
     "requested":2,"results":[row()]},
    {"selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
     "requested":1,"results":[{"status":"AUDITED"}]},
    {"selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
     "requested":1,"results":[row("UNKNOWN")]},
])
def test_requires_explicit_authorized_batch_contract(wrong):
    with pytest.raises(ValueError):
        build(wrong)


def test_saved_history_route_calls_authorized_packet_builder():
    from pathlib import Path
    code=(Path(__file__).resolve().parents[1]/
          "app"/"assistant_saved_history_eval.py").read_text(encoding="utf-8")
    assert 'result["human_review_packet"]=build_authorized_saved_reply_review_packet(result)' in code
    assert 'AssistantThread.user_id==user_id' in code
    assert 'resolve_mixed_audit_sources(db,batch_principal,audit)' in code



def test_duplicate_or_invalid_uuid_of_audited_saved_replies_is_rejected():
    with pytest.raises(ValueError,match="Duplicate"):
        build(batch([row(),row()]))
    invalid=row()
    invalid["thread_id"]="AAAAAAAA-PRIV-ATEX-TTTT-123456789012"
    with pytest.raises(ValueError,match="identifier"):
        build(batch([invalid]))


def test_unavailable_records_are_not_in_review_packet():
    packet=build(batch([
        row("INELIGIBLE"),row("SOURCE_UNAVAILABLE"),row("UNAVAILABLE")]))
    assert packet["review_ready_replies"]==0
    assert packet["ineligible_or_unavailable_replies"]==3
    assert packet["items"]==[]
    assert packet["human_review_completed"] is False
