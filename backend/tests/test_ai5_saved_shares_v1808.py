"""AI-5 v180.8 save/share security and persistence contract tests.

Deterministic SQLite tests, no external API spend and no Supabase mutations.
"""
import json
import uuid
from datetime import datetime,timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import User,AccessGrant
from app.access import profile
from app.ai5 import persistence as p,state
from app.ai5 import api


@pytest.fixture
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
    state.storage.STORES.clear()


@pytest.fixture
def users(db):
    result=[]
    for index in range(3):
        user=User(email=f"officer{index}@example.gov",full_name=f"Officer {index}",
                  password_hash="fixture-only")
        db.add(user);db.flush()
        grant=AccessGrant(user_id=user.id,access_role="National Analyst",
                          geographic_scope="Nationwide",province="",
                          permissions_json=json.dumps({"view_intelligence":True}),
                          status="Active")
        db.add(grant)
        result.append(user)
    db.commit()
    return result


def turn(question="What happened?",mode="WEB_ONLY",identifier=None,attachment=False):
    ident=identifier or uuid.uuid4().hex
    public={"id":"WEB-FIX-01","type":"PUBLIC_REPORT","title":"Report A",
            "url":"https://example.org/report","published_at":"2024-06-01",
            "read_status":"READ","basis":"LIVE_PUBLIC_LOOKUP","excerpt":"Public evidence."}
    attachments=[{"id":"ATT-FIX-1","type":"ATTACHMENT_FILE",
                 "title":"Private uploaded document","excerpt":"SECRET UPLOADED TEXT"}] if attachment else []
    return {"turn_id":ident,"question":question,"mode":"GENERAL_RESEARCH",
        "action_mode":"OPERATIONAL","source_mode":mode,
        "answer":{"body":"## Observation\nA documented example [[WEB-FIX-01]].",
                  "draft":"Editable draft","table":{"title":"","columns":[],"rows":[]},
                  "open_questions":[]},
        "sources":[public,*attachments],"used_saved":mode=="WEB_SMARTRADAR",
        "used_attachment":attachment,"used_public":True,
        "searched_at":"2026-11-24",
        "research_trace":{"sources":[public,*attachments],
                          "model_source_ids":["WEB-FIX-01"],
                          "cited_source_ids":["WEB-FIX-01"]}}


def put(user,grant,conv,record):
    state.add_turn(user,conv,grant,record)


def test_save_survives_session_expiration_and_auto_appends_after_reopen(db,users):
    owner=users[0]; grant=profile(db,owner); cid=str(uuid.uuid4())
    original=turn("Compare institutions.")
    put(owner,grant,cid,original)
    row=p.create_saved(db,owner,grant,cid,"Important research",
                       {original["turn_id"]:"Officer-edited draft"})
    assert row["title"]=="Important research"
    assert row["messages"][1]["data"]["answer"]["draft"]=="Officer-edited draft"
    assert len(p.list_saved(db,owner,grant)["saved_chats"])==1
    assert p.list_saved(db,users[1],profile(db,users[1]))["saved_chats"]==[]
    p.rename_saved(db,owner,row["id"],"Renamed chat")
    assert p.list_saved(db,owner,grant)["saved_chats"][0]["title"]=="Renamed chat"

    # Simulate a 12-hour cache expiry or process restart.
    state.storage.STORES.clear()
    restored=p.open_saved(db,owner,grant,row["id"])
    assert restored["message_count"]==2
    assert restored["messages"][1]["data"]["answer"]["body"].startswith("## Observation")
    assert restored["messages"][1]["data"]["answer"]["draft"]=="Officer-edited draft"
    assert len(state.turns(owner,cid,grant))==1
    latest=turn("What changed since the last example?")
    put(owner,grant,cid,latest)
    result=p.auto_append(db,owner,grant,cid,latest)
    assert result["status"]=="SAVED"
    assert p.sync_pending(db,owner,grant,row["id"])["answer_count"]==2
    state.storage.STORES.clear()
    reopened=p.open_saved(db,owner,grant,row["id"])
    assert reopened["message_count"]==4
    assert reopened["messages"][-2]["text"]=="What changed since the last example?"
    assert reopened["messages"][-1]["data"]["turn_id"]==latest["turn_id"]


def test_owner_only_rename_delete_and_draft_revision(db,users):
    owner,other=users[:2]; grant=profile(db,owner)
    cid=str(uuid.uuid4());record=turn()
    put(owner,grant,cid,record)
    row=p.create_saved(db,owner,grant,cid,"Saved",{})
    with pytest.raises(HTTPException) as e:p.open_saved(db,other,profile(db,other),row["id"])
    assert e.value.status_code==404
    with pytest.raises(HTTPException) as e:p.rename_saved(db,other,row["id"],"stolen")
    assert e.value.status_code==404
    with pytest.raises(HTTPException) as e:p.delete_saved(db,other,row["id"])
    assert e.value.status_code==404
    assert p.save_draft(db,owner,row["id"],record["turn_id"],"Revised content")["ok"]
    assert p.open_saved(db,owner,grant,row["id"])["messages"][1]["data"]["answer"]["draft"]=="Revised content"
    with pytest.raises(HTTPException) as e:p.save_draft(db,owner,row["id"],"bad-id","corruption")
    assert e.value.status_code==404
    assert p.delete_saved(db,owner,row["id"])["ok"]
    with pytest.raises(HTTPException) as e:p.open_saved(db,owner,grant,row["id"])
    assert e.value.status_code==404


def test_saved_attachment_text_excluded_and_scope_rechecked(db,users):
    owner=users[0];grant=profile(db,owner);cid=str(uuid.uuid4())
    private=turn(mode="WEB_SMARTRADAR",attachment=True)
    put(owner,grant,cid,private)
    row=p.create_saved(db,owner,grant,cid,"Restricted",{})
    stored=p._owned(db,owner,row["id"])
    assert "SECRET UPLOADED TEXT" not in stored.turns_json
    assert "Private uploaded document" in stored.turns_json
    assert p.open_saved(db,owner,grant,row["id"])["message_count"]==2
    db.query(AccessGrant).filter_by(user_id=owner.id).update({"province":"Changed"})
    db.commit()
    with pytest.raises(HTTPException) as e:p.open_saved(db,owner,profile(db,owner),row["id"])
    assert e.value.status_code==403


def test_share_one_answer_read_only_recipient_only_expiry_revoke(db,users):
    owner,recipient,outsider=users;grant=profile(db,owner)
    cid=str(uuid.uuid4());first=turn("First question");second=turn("Second question")
    put(owner,grant,cid,first);put(owner,grant,cid,second)
    emails=[recipient.email]
    preview=p.share_preview(db,owner,grant,cid,"ANSWER",second["turn_id"],emails,False)
    assert preview["can_share"]
    assert preview["selected_count"]==1
    assert preview["preview"]["answers"][0]["question"]=="Second question"
    created=p.create_share(db,owner,grant,{"conversationId":cid,"scope":"ANSWER",
        "turnId":second["turn_id"],"recipients":emails,
        "includeResearchTrail":False,"expiryDays":7,
        "previewDigest":preview["preview_digest"]})
    assert created["token"]
    opened=p.open_share(db,recipient,profile(db,recipient),created["token"])
    assert opened["read_only"]
    assert len(opened["snapshot"]["answers"])==1
    assert opened["snapshot"]["answers"][0]["question"]=="Second question"
    assert opened["snapshot"]["answers"][0]["sources"][0]["title"]=="Report A"
    assert "research_trail" not in opened["snapshot"]["answers"][0]
    with pytest.raises(HTTPException) as e:p.open_share(
        db,outsider,profile(db,outsider),created["token"])
    assert e.value.status_code==403
    assert p.revoke_share(db,owner,created["id"])["status"]=="REVOKED"
    assert db.get(p.AI5SharedSnapshot,created["id"]).snapshot_json=="{}"
    with pytest.raises(HTTPException) as e:p.open_share(
        db,recipient,profile(db,recipient),created["token"])
    assert e.value.status_code==404


def test_share_freezes_snapshot_and_requires_updated_preview(db,users):
    owner,recipient=users[:2];grant=profile(db,owner);cid=str(uuid.uuid4())
    original=turn("Original question");put(owner,grant,cid,original)
    email=[recipient.email]
    preview=p.share_preview(db,owner,grant,cid,"CONVERSATION",None,email,True)
    changed=turn("Added after preview");put(owner,grant,cid,changed)
    with pytest.raises(HTTPException) as e:p.create_share(db,owner,grant,{
        "conversationId":cid,"scope":"CONVERSATION","recipients":email,
        "includeResearchTrail":True,"expiryDays":1,
        "previewDigest":preview["preview_digest"]})
    assert e.value.status_code==409
    fresh=p.share_preview(db,owner,grant,cid,"CONVERSATION",None,email,True)
    shared=p.create_share(db,owner,grant,{
        "conversationId":cid,"scope":"CONVERSATION","recipients":email,
        "includeResearchTrail":True,"expiryDays":1,
        "previewDigest":fresh["preview_digest"]})
    later=turn("Added after sharing");put(owner,grant,cid,later)
    view=p.open_share(db,recipient,profile(db,recipient),shared["token"])
    assert len(view["snapshot"]["answers"])==2
    assert "research_trail" in view["snapshot"]["answers"][0]
    assert "model_passages" not in view["snapshot"]["answers"][0]["research_trail"]
    # Expiry and access are rechecked on every use.
    row=db.get(p.AI5SharedSnapshot,shared["id"])
    row.expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    with pytest.raises(HTTPException) as e:p.open_share(
        db,recipient,profile(db,recipient),shared["token"])
    assert e.value.status_code==404


def test_share_flags_internal_sources_and_allows_narrowing(db,users):
    owner,recipient=users[:2];grant=profile(db,owner);cid=str(uuid.uuid4())
    public=turn("Public finding");mixed=turn("Internal analysis",mode="WEB_SMARTRADAR")
    mixed["sources"].append({"id":"SAVED-FIX-1","type":"SAVED_SOCIAL",
                              "title":"Restricted record"})
    put(owner,grant,cid,public);put(owner,grant,cid,mixed)
    email=[recipient.email]
    broad=p.share_preview(db,owner,grant,cid,"CONVERSATION",None,email,False)
    assert not broad["can_share"] and broad["blocked_content"]
    with pytest.raises(HTTPException) as e:p.create_share(db,owner,grant,{
        "conversationId":cid,"scope":"CONVERSATION","recipients":email,
        "includeResearchTrail":False,"previewDigest":broad["preview_digest"]})
    assert e.value.status_code==409
    narrowed=p.share_preview(db,owner,grant,cid,"ANSWER",public["turn_id"],email,False)
    assert narrowed["can_share"]
    share=p.create_share(db,owner,grant,{
        "conversationId":cid,"scope":"ANSWER","turnId":public["turn_id"],
        "recipients":email,"includeResearchTrail":False,
        "previewDigest":narrowed["preview_digest"]})
    assert p.open_share(db,recipient,profile(db,recipient),share["token"])["snapshot"]["answers"][0]["question"]=="Public finding"
    # Current recipient permissions are always required, even for public-only shares.
    db.query(AccessGrant).filter_by(user_id=recipient.id).update({"status":"Inactive"})
    db.commit()
    with pytest.raises(HTTPException) as e:p.open_share(
        db,recipient,profile(db,recipient),share["token"])
    assert e.value.status_code==403


def test_deleting_saved_chat_revokes_its_snapshot_links(db,users):
    owner,recipient=users[:2];grant=profile(db,owner);cid=str(uuid.uuid4())
    original=turn();put(owner,grant,cid,original)
    saved=p.create_saved(db,owner,grant,cid,"Saved",{})
    prev=p.share_preview(db,owner,grant,cid,"ANSWER",original["turn_id"],[recipient.email],False)
    share=p.create_share(db,owner,grant,{"conversationId":cid,"scope":"ANSWER",
        "turnId":original["turn_id"],"recipients":[recipient.email],
        "previewDigest":prev["preview_digest"]})
    assert p.open_share(db,recipient,profile(db,recipient),share["token"])
    p.delete_saved(db,owner,saved["id"])
    with pytest.raises(HTTPException) as e:p.open_share(
        db,recipient,profile(db,recipient),share["token"])
    assert e.value.status_code==404


def test_routes_are_authenticated_and_read_only_shares_are_not_export_endpoints():
    rules={(r.path,tuple(sorted(r.methods or []))) for r in api.router.routes}
    for verb,path in [("GET","/api/ai-5/saved"),("POST","/api/ai-5/saved"),
                      ("GET","/api/ai-5/saved/{saved_id}"),
                      ("POST","/api/ai-5/saved/{saved_id}/sync"),
                      ("PATCH","/api/ai-5/saved/{saved_id}/draft"),
                      ("POST","/api/ai-5/shared/preview"),
                      ("POST","/api/ai-5/shared"),
                      ("GET","/api/ai-5/shared/view/{token}"),
                      ("DELETE","/api/ai-5/shared/{share_id}")]:
        assert any(pth==path and verb in methods for pth,methods in rules)
    assert not any("/shared" in pth and "/export" in pth for pth,_ in rules)
