"""BAWASLU AI-5 v183.4 automatic private history regression tests.

All fixtures are synthetic. No paid model calls, database migrations or
existing officer records are involved.
"""
import json
import uuid

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import User, AccessGrant
from app.access import profile
from app.ai5 import persistence as p, state, api


@pytest.fixture()
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    state.storage.STORES.clear()
    engine.dispose()


@pytest.fixture()
def people(db):
    users=[]
    for index in range(2):
        user=User(email=f"autohistory{index}@example.gov",
                  full_name=f"Officer {index}",password_hash="synthetic-only")
        db.add(user);db.flush()
        db.add(AccessGrant(user_id=user.id,access_role="National Analyst",
                           geographic_scope="Nationwide",province="",
                           permissions_json=json.dumps({"view_intelligence":True}),
                           status="Active"))
        users.append(user)
    db.commit()
    return users


def sample(question="Compare incident handling across provinces",
           title="Incident Handling Across Provinces",scope="WEB_ONLY"):
    return {
        "turn_id":uuid.uuid4().hex,"question":question,
        "answer":{"title":title,"body":"## Main finding\nEvidence-based comparison.",
                  "draft":"Editable draft","table":{"title":"","columns":[],"rows":[]},
                  "open_questions":[]},
        "source_mode":scope,"mode":"GENERAL_RESEARCH",
        "action_mode":"OPERATIONAL","sources":[],"used_saved":scope!="WEB_ONLY",
        "research_trace":{"sources":[]}}


def test_first_answer_auto_creates_owner_private_chat_without_manual_save(db,people):
    owner,other=people;grant=profile(db,owner)
    cid=str(uuid.uuid4())
    first=sample()
    state.add_turn(owner,cid,grant,first)
    result=p.auto_append(db,owner,grant,cid,first)
    assert result["status"]=="SAVED" and result["created"] is True
    assert result["title"]=="Incident Handling Across Provinces"
    assert db.query(func.count(p.AI5SavedChat.id)).scalar()==1
    assert p.list_saved(db,other,profile(db,other))["saved_chats"]==[]
    state.storage.STORES.clear()
    saved=p.open_saved(db,owner,grant,result["saved_chat_id"])
    assert saved["message_count"]==2
    assert saved["messages"][0]["text"]==first["question"]
    assert saved["messages"][1]["data"]["answer"]["title"]==result["title"]
    assert len(state.turns(owner,cid,grant))==1


def test_followup_autosaves_under_same_record_and_preserves_rename(db,people):
    owner=people[0];grant=profile(db,owner);cid=str(uuid.uuid4())
    first=sample()
    state.add_turn(owner,cid,grant,first)
    created=p.auto_append(db,owner,grant,cid,first)
    p.rename_saved(db,owner,created["saved_chat_id"],"Officer custom title")
    second=sample("What changes if another province is added?",
                  "Different automatically generated title")
    state.add_turn(owner,cid,grant,second)
    latest=p.auto_append(db,owner,grant,cid,second)
    assert latest["status"]=="SAVED" and latest["created"] is False
    assert latest["saved_chat_id"]==created["saved_chat_id"]
    # Retrying the same server turn must not duplicate messages.
    assert p.auto_append(db,owner,grant,cid,second)["status"]=="SAVED"
    assert db.query(func.count(p.AI5SavedChat.id)).scalar()==1
    state.storage.STORES.clear()
    reopened=p.open_saved(db,owner,grant,created["saved_chat_id"])
    assert reopened["message_count"]==4
    assert reopened["title"]=="Officer custom title"
    assert reopened["messages"][-1]["data"]["turn_id"]==second["turn_id"]


def test_legacy_manual_save_retry_is_idempotent_after_automatic_creation(db,people):
    owner=people[0];grant=profile(db,owner);cid=str(uuid.uuid4())
    first=sample()
    state.add_turn(owner,cid,grant,first)
    created=p.auto_append(db,owner,grant,cid,first)
    # The retry route is safe even if a server-side first save succeeded but
    # the browser missed its response.
    retried=p.create_saved(db,owner,grant,cid,"Do not replace existing title",{})
    assert retried["id"]==created["saved_chat_id"]
    assert retried["title"]==created["title"]
    assert retried["message_count"]==2
    assert db.query(func.count(p.AI5SavedChat.id)).scalar()==1


def test_auto_save_never_shares_and_rechecks_restricted_access(db,people):
    owner,other=people;grant=profile(db,owner);cid=str(uuid.uuid4())
    turn=sample("Summarise authorised records","Restricted officer notes",
                scope="WEB_SMARTRADAR")
    state.add_turn(owner,cid,grant,turn)
    created=p.auto_append(db,owner,grant,cid,turn)
    assert created["status"]=="SAVED"
    assert db.query(func.count(p.AI5SharedSnapshot.id)).scalar()==0
    with pytest.raises(Exception) as unauthorized:
        p.open_saved(db,other,profile(db,other),created["saved_chat_id"])
    assert unauthorized.value.status_code==404
    db.query(AccessGrant).filter_by(user_id=owner.id).update({"province":"Changed"})
    db.commit()
    with pytest.raises(Exception) as changed:
        p.open_saved(db,owner,profile(db,owner),created["saved_chat_id"])
    assert changed.value.status_code==403


def test_limit_failure_is_visible_and_does_not_overwrite_old_chats(db,people):
    owner=people[0];grant=profile(db,owner)
    for i in range(p.MAX_SAVED):
        db.add(p.AI5SavedChat(id=str(uuid.uuid4()),owner_user_id=owner.id,
          conversation_id=str(uuid.uuid4()),title=f"Preserved chat {i}",
          turns_json="[]",draft_revisions_json="{}",
          scope_fingerprint=state.fingerprint(grant)))
    db.commit()
    result=p.auto_append(db,owner,grant,str(uuid.uuid4()),sample())
    assert result["status"]=="COULD_NOT_SAVE"
    assert "40 saved chats" in result["reason"]
    assert db.query(func.count(p.AI5SavedChat.id)).scalar()==p.MAX_SAVED


def test_auto_title_uses_existing_model_answer_and_falls_back_to_question():
    assert p._auto_title(sample(title="Useful regional findings"))=="Useful regional findings"
    assert p._auto_title(sample(title="Research"))=="Compare incident handling across provinces"
    assert p._auto_title(sample(title=" "))=="Compare incident handling across provinces"
    assert len(p._auto_title(sample(title="Title "+"A"*300)))<=96


def test_api_chat_persists_first_answer_and_reports_saved_chat_id(db,people,monkeypatch):
    """The actual /chat handler must return the server-created identifier."""
    owner=people[0]
    monkeypatch.setenv("OPENAI_API_KEY","")
    monkeypatch.setattr(api.web,"research",lambda *args,**kwargs:{
      "status":"NOT_NEEDED","sources":[],"as_of":"2026-11-25",
      "attempts":[],"dimensions":[],"coverage":[],
      "evidence_intent":"GENERAL"})
    monkeypatch.setattr(api.engine,"generate",lambda *args,**kwargs:({
      "title":"Climate and infrastructure observations",
      "body":"Public evidence should be verified.","draft":"",
      "table":{"title":"","columns":[],"rows":[]},"open_questions":[],
      "source_ids":[]}, "COMPLETE"))
    cid=str(uuid.uuid4())
    data={"question":"Explain infrastructure observations",
          "conversationId":cid,"sourceMode":"WEB_ONLY",
          "mode":"GENERAL_RESEARCH"}
    response=api.chat(data,owner,db)
    assert response["save_status"]=="SAVED"
    assert response["saved_chat_id"]
    stored=p.open_saved(db,owner,profile(db,owner),response["saved_chat_id"])
    assert stored["title"]=="Climate and infrastructure observations"
    assert stored["message_count"]==2
    state.storage.STORES.clear()
    next_response=api.chat({"question":"What are the next steps?",
      "conversationId":cid,"sourceMode":"WEB_ONLY",
      "mode":"GENERAL_RESEARCH"},owner,db)
    assert next_response["save_status"]=="SAVED"
    assert next_response["saved_chat_id"]==response["saved_chat_id"]
    assert p.open_saved(db,owner,profile(db,owner),
                        response["saved_chat_id"])["message_count"]==4
