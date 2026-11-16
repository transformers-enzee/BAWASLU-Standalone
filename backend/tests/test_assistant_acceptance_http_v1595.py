"""v159.5 two-administrator end-to-end HTTP QA, entirely in isolated SQLite.

Uses the real auth token, access grants, API routing, database writes and
append-only history. NEVER touches Render/Supabase staging evidence records.
"""
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import Base,get_db
from app.main import app
from app.models import User,AccessGrant,AssistantAcceptanceEvidence,AssistantAcceptanceEvidenceEvent
from app.access import default_permissions
from app.auth import create_session

ROOT="/api/assistant-evaluation/acceptance-submissions"

@pytest.fixture()
def environment():
    engine=create_engine("sqlite:///:memory:",connect_args={"check_same_thread":False},
                         poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)
    with factory() as db:
        roles=((1,"National Administrator","Nationwide","Active"),
               (2,"National Administrator","Nationwide","Active"),
               (3,"Viewer","Nationwide","Active"),
               (4,"National Administrator","Nationwide","Inactive"),
               (5,"National Administrator","Province","Active"))
        for uid,role,scope,status in roles:
            db.add(User(id=uid,email=f"acceptance-qa-{uid}@example.invalid",
                        full_name=f"QA User {uid}",password_hash="unused"))
            db.add(AccessGrant(user_id=uid,access_role=role,geographic_scope=scope,
                status=status,permissions_json=json.dumps(default_permissions(role))))
        db.commit()
        tokens={}
        for uid,_,_,_ in roles:
            tokens[uid]={"Authorization":"Bearer "+create_session(db,db.get(User,uid))}
    def isolated_db():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=isolated_db
    try:
        yield TestClient(app),factory,tokens
    finally:
        app.dependency_overrides.pop(get_db,None)
        engine.dispose()

def test_two_admin_authenticated_http_review_and_no_formal_signoff(environment):
    client,factory,tokens=environment
    assert client.get(ROOT).status_code==401
    assert client.get(ROOT,headers=tokens[3]).status_code==403
    assert client.get(ROOT,headers=tokens[4]).status_code==403
    assert client.get(ROOT,headers=tokens[5]).status_code==403
    payload={"track":"SOURCE_LINKED_AI_REVIEW","reference":"qa:isolated-2026-0001"}
    made=client.post(ROOT,json=payload,headers=tokens[1])
    assert made.status_code==200,made.text
    entry=made.json()
    assert entry["status"]=="SUBMITTED_UNVERIFIED"
    assert made.headers["cache-control"]=="private, no-store"
    assert entry["history"][0]["actor_user_id"]==1
    assert entry["client_acceptance"] is False
    assert client.post(ROOT+"/"+str(entry["id"])+"/review",
        json={"action":"EVIDENCE_REVIEWED"},headers=tokens[1]).status_code==409
    reviewed=client.post(ROOT+"/"+str(entry["id"])+"/review",
        json={"action":"EVIDENCE_REVIEWED"},headers=tokens[2])
    assert reviewed.status_code==200,reviewed.text
    assert reviewed.json()["status"]=="REVIEWED"
    assert [e["action"] for e in reviewed.json()["history"]]==[
        "SUBMITTED","EVIDENCE_REVIEWED"]
    assert reviewed.json()["legal_signoff"] is False
    assert reviewed.json()["client_acceptance"] is False
    repeated=client.post(ROOT+"/"+str(entry["id"])+"/review",
        json={"action":"REVISION_REQUESTED"},headers=tokens[2])
    assert repeated.status_code==409
    listing=client.get(ROOT,headers=tokens[1])
    assert listing.status_code==200,listing.text
    assert listing.headers["cache-control"]=="private, no-store"
    assert listing.json()["status_counts"]=={"REVIEWED":1}
    assert listing.json()["formal_legal_signoff_verified"] is False
    assert listing.json()["formal_client_acceptance_verified"] is False
    with factory() as db:
        assert db.query(AssistantAcceptanceEvidence).count()==1
        events=db.query(AssistantAcceptanceEvidenceEvent).order_by(
            AssistantAcceptanceEvidenceEvent.id).all()
        assert [ev.action for ev in events]==["SUBMITTED","EVIDENCE_REVIEWED"]
        assert events[0].actor_id!=events[1].actor_id

def test_revision_and_duplicate_review_is_preserved_across_http(environment):
    client,factory,tokens=environment
    payload={"track":"LEGAL_REFERENCE_SIGNOFF","reference":"document:legal-2026-v1"}
    initial=client.post(ROOT,json=payload,headers=tokens[1]).json()
    revised=client.post(ROOT+"/"+str(initial["id"])+"/review",
        json={"action":"REVISION_REQUESTED"},headers=tokens[2])
    assert revised.status_code==200
    assert revised.json()["status"]=="REVISION_REQUESTED"
    assert client.post(ROOT+"/"+str(initial["id"])+"/review",
        json={"action":"EVIDENCE_REVIEWED"},headers=tokens[2]).status_code==409
    new=client.post(ROOT,json={"track":payload["track"],
        "reference":"document:legal-2026-v2"},headers=tokens[1])
    assert new.status_code==200
    assert new.json()["id"]!=initial["id"]
    assert new.json()["status"]=="SUBMITTED_UNVERIFIED"
    assert client.get(ROOT,headers=tokens[1]).json()["status_counts"]=={
        "SUBMITTED_UNVERIFIED":1,"REVISION_REQUESTED":1}
    with factory() as db:
        assert db.query(AssistantAcceptanceEvidence).count()==2
        assert db.query(AssistantAcceptanceEvidenceEvent).count()==3

@pytest.mark.parametrize("ref",[
    "https://example.invalid/document",
    "../../private-file",
    "=HYPERLINK(1)",
    "x",
])
def test_untrusted_reference_denied_via_actual_http(environment,ref):
    client,factory,tokens=environment
    r=client.post(ROOT,json={
        "track":"FORMAL_CLIENT_ACCEPTANCE","reference":ref},headers=tokens[1])
    assert r.status_code==422
    with factory() as db:
        assert db.query(AssistantAcceptanceEvidence).count()==0

def test_invalid_review_action_and_unknown_id_leave_audit_unchanged(environment):
    client,factory,tokens=environment
    one=client.post(ROOT,json={
        "track":"NEGATIVE_CONTROL_REVIEW","reference":"qa:missing-source-control"},
        headers=tokens[1]).json()
    assert client.post(ROOT+"/"+str(one["id"])+"/review",
        json={"action":"LEGAL_APPROVED"},headers=tokens[2]).status_code==422
    assert client.post(ROOT+"/999999/review",
        json={"action":"EVIDENCE_REVIEWED"},headers=tokens[2]).status_code==404
    with factory() as db:
        assert db.query(AssistantAcceptanceEvidenceEvent).count()==1

def test_no_live_database_connection_or_external_ai_calls(environment):
    client,factory,tokens=environment
    assert client.get(ROOT,headers=tokens[1]).status_code==200
    with factory() as db:
        assert db.bind.dialect.name=="sqlite"
        assert db.query(AssistantAcceptanceEvidence).count()==0
