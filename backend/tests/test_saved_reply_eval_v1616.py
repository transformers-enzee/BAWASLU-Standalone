"""Owned historical reply auditing: real saved text, fresh source access, no AI."""
import json
from datetime import datetime
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException,Response
from app.db import Base
from app.assistant_history import AssistantThread
from app import assistant_saved_history_eval as history_eval

@pytest.fixture
def session(monkeypatch):
    engine=create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine,tables=[AssistantThread.__table__])
    with Session(engine) as db:
        def insert(tid,owner,messages):
            db.add(AssistantThread(id=tid,user_id=owner,title="Private question",
                messages_json=json.dumps(messages),created_at=datetime(2026,11,1),
                updated_at=datetime(2026,11,2)))
            db.commit()
        insert("11111111-1111-4111-8111-111111111111",3,[
            {"role":"user","text":"What does saved monitoring support?"},
            {"role":"assistant","text":"One post raises a concern [SOCIAL-7].",
             "records":[{"record_type":"SOCIAL_LISTENING","id":"SOCIAL-7",
                         "source_excerpt":"A historical post snapshot; do not trust it"}]}])
        insert("22222222-2222-4222-8222-222222222222",4,[
            {"role":"user","text":"Other user's question"},
            {"role":"assistant","text":"Other answer [SOCIAL-8].",
             "records":[{"id":"SOCIAL-8"}]}])
        monkeypatch.setattr(history_eval,"profile",
            lambda db,user:{"status":"Active","permissions":{"view_intelligence":True}})
        yield db
    engine.dispose()

def current():return SimpleNamespace(id=3)

def req(thread="11111111-1111-4111-8111-111111111111",index=1):
    return history_eval.SavedReplyAuditRequest(thread_id=thread,
                                              answer_message_index=index)

def test_only_owned_replies_are_listed_without_answer_or_question(session):
    response=Response()
    data=history_eval.saved_reply_candidates(response,40,current(),session)
    assert data["candidate_count"]==1
    assert data["eligible_count"]==1
    assert data["candidates"][0]["saved_source_count"]==1
    assert data["includes_answer_text"] is False
    assert data["model_answers_generated"]==0
    assert response.headers["Cache-Control"]=="private, no-store"
    assert "One post raises" not in json.dumps(data)
    assert "Other user's question" not in json.dumps(data)
    assert "historical post snapshot" not in json.dumps(data)

def test_owned_saved_reply_uses_fresh_reauthorized_source_not_snapshot(session,monkeypatch):
    seen={}
    def fresh(db,principal,request):
        seen["ids"]=request.source_ids
        return [{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                 "source_excerpt":"Current authorized source text; not stored snapshot"}]
    monkeypatch.setattr(history_eval,"resolve_mixed_audit_sources",fresh)
    response=Response()
    data=history_eval.saved_reply_audit(req(),response,current(),session)
    assert seen["ids"]==["SOCIAL-7"]
    assert data["history_content_user_editable"] is True
    assert data["original_model_generation_provenance_verified"] is False
    assert data["fresh_source_scope_count"]==1
    assert data["audit"]["schema"]=="BAWASLU_MIXED_ANSWER_AUDIT_V1609"
    assert data["audit"]["human_accuracy"] is None
    assert data["model_calls"]==0 and data["database_writes"]==0
    assert data["saved_thread_modified"] is False
    assert "Current authorized source text" not in json.dumps(data)
    assert "historical post snapshot" not in json.dumps(data)
    assert "One post raises" not in json.dumps(data)
    assert response.headers["X-Acceptance-Status"]=="PENDING_HUMAN_REVIEW"

def test_other_users_thread_cannot_be_inspected(session):
    with pytest.raises(HTTPException) as e:
        history_eval.saved_reply_audit(req("22222222-2222-4222-8222-222222222222"),
            Response(),current(),session)
    assert e.value.status_code==404

def test_inactive_profile_is_forbidden(session,monkeypatch):
    monkeypatch.setattr(history_eval,"profile",
        lambda db,user:{"status":"Inactive","permissions":{"view_intelligence":True}})
    with pytest.raises(HTTPException) as e:
        history_eval.saved_reply_candidates(Response(),40,current(),session)
    assert e.value.status_code==403

def test_stale_source_permissions_fail_entire_audit(session,monkeypatch):
    def denied(*args):
        raise HTTPException(404,"Source not currently authorized")
    monkeypatch.setattr(history_eval,"resolve_mixed_audit_sources",denied)
    with pytest.raises(HTTPException) as e:
        history_eval.saved_reply_audit(req(),Response(),current(),session)
    assert e.value.status_code==404

@pytest.mark.parametrize("index",[-1,0,8,60])
def test_invalid_turn_is_rejected(session,index):
    if index<1 or index>59:
        with pytest.raises(Exception):
            req(index=index)
    else:
        with pytest.raises(HTTPException) as e:
            history_eval.saved_reply_audit(req(index=index),Response(),current(),session)
        assert e.value.status_code==422

def test_historical_social_ids_resolve_without_record_id():
    messages=[{"role":"user","text":"Explain the posts"},
              {"role":"assistant","text":"A post was collected [SOCIAL-197].",
               "records":[{"record_type":"SOCIAL_LISTENING","id":"SOCIAL-197",
                           "intelligence_id":"SOCIAL-197","source_post_id":"197"}]}]
    scope=history_eval._reply_scope(messages,1)
    assert scope["eligible"] and scope["source_ids"]==["SOCIAL-197"]

def test_original_source_card_limit_is_not_silently_truncated():
    messages=[{"role":"user","text":"Explain all sources"},
              {"role":"assistant","text":"Lots of evidence [SOCIAL-1].",
               "records":[{"id":f"SOCIAL-{i}"} for i in range(1,14)]}]
    scope=history_eval._reply_scope(messages,1)
    assert scope["eligible"] is False
    assert scope["reason_code"]=="SAVED_EVIDENCE_SCOPE_EXCEEDS_LIMIT"

def test_invalid_card_cannot_forge_source_scope():
    messages=[{"role":"user","text":"Explain the sources"},
              {"role":"assistant","text":"Maybe something [SOCIAL-1].",
               "records":[{"id":"SOCIAL-1","source_excerpt":"original"},
                          {"record_id":"../../../data/private"}]}]
    assert history_eval._reply_scope(messages,1)["eligible"] is False

def test_wrong_question_order_disallows_audit():
    messages=[{"role":"assistant","text":"Answer [SOCIAL-1].","records":[{"id":"SOCIAL-1"}]},
              {"role":"assistant","text":"Later answer [SOCIAL-1].","records":[{"id":"SOCIAL-1"}]}]
    assert history_eval._reply_scope(messages,1)["eligible"] is False

def test_user_editable_history_never_becomes_model_provenance(session,monkeypatch):
    monkeypatch.setattr(history_eval,"resolve_mixed_audit_sources",
        lambda *args:[{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                      "source_excerpt":"Current source"}])
    result=history_eval.saved_reply_audit(req(),Response(),current(),session)
    assert result["original_model_generation_provenance_verified"] is False
    assert result["factual_accuracy_verified"] is False
    assert result["legal_signoff_verified"] is False
