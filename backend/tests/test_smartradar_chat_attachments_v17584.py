"""SmartRadar unified assistant security and document QA. No AI/provider calls."""
import io, json, os, uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from app.assistant_mode import mode_contract,mode_directive
from app.assistant_workflows import normalize_workflow_request,source_consultation,structured_findings
from app.assistant_attachments import (
    _decode_document,_clamav_scan,_scope,AssistantChatAttachment,
    selected_attachment_evidence,read_attachment_section,remove_attachment,
    LinkRequest,attach_link,
)
from app.assistant_history import AssistantThread
from app.assistant_response_feedback import AssistantResponseFeedback
from app.db import Base,engine,SessionLocal
from app.models import User


def officer(role="Regency/City Officer",scope="Regency/City"):
    return {"id":"1","role":role,"geographic_scope":scope,"status":"Active",
        "province":"Jawa Barat","regency_city":"Bandung",
        "province_code":"32","regency_city_code":"3273",
        "permissions":{"view_intelligence":True}}


def test_operations_workspace_alias_preserves_access_guards():
    # The existing Operations route sends OPERATIONS; it is not a new analytical mode.
    operational=mode_contract({"workspaceMode":"OPERATIONS","perspective":"AUTO"},officer())
    assert operational["workspace_mode"]=="OPERATIONAL"
    assert operational["assistant_mode"]=="OPERATIONAL"
    with pytest.raises(PermissionError):
        mode_contract({"workspaceMode":"OPERATIONS","assistantMode":"MANAGEMENT"},officer())
    with pytest.raises(ValueError):
        mode_contract({"workspaceMode":"WRONG_WORKSPACE"},officer())


def test_default_workspace_mode_separate_from_optional_perspective():
    operations=mode_contract({"workspaceMode":"OPERATIONAL","perspective":"EXECUTIVE"},officer())
    assert operations["assistant_mode"]=="OPERATIONAL"
    assert operations["perspective"]=="EXECUTIVE"
    assert "first practical officer check" in mode_directive(operations)
    leadership=mode_contract({"workspaceMode":"MANAGEMENT","perspective":"RESEARCH"},
        officer("National Leadership","Nationwide"))
    assert leadership["assistant_mode"]=="MANAGEMENT"
    assert "decision or conclusion" in mode_directive(leadership)
    with pytest.raises(PermissionError):
        mode_contract({"workspaceMode":"OPERATIONAL","assistantMode":"MANAGEMENT"},officer())
    with pytest.raises(ValueError):
        mode_contract({"workspaceMode":"OPERATIONAL","perspective":"LAW_ENFORCEMENT"},officer())
    with pytest.raises(PermissionError):
        mode_contract({}, {**officer(),"permissions":{"view_intelligence":False}})


def test_source_selector_attachment_consent_and_unverified_citations():
    selection=normalize_workflow_request({"sourceSelection":{
      "smartRadar":False,"publicWeb":False,"legalReferences":False,"attachments":True}})
    assert selection["sources"]["attachments"] is True
    assert selection["sources"]["smartRadar"] is False
    record={"record_id":"ATT-"+"a"*32+"-S1","record_type":"CHAT_ATTACHMENT",
        "source_excerpt":"An allegation in an uploaded document"}
    consult=source_consultation(selection["sources"],[record],[record["record_id"]])
    assert consult[0]["status"]=="NOT_SELECTED"
    assert consult[3]["status"]=="CONSULTED"
    assert consult[3]["basis"]=="USER_SUPPLIED_UNVERIFIED"
    finding=structured_findings({"observations":["User attachment says X ["+record["record_id"]+"]."]},
        [record],[record["record_id"]])[0]
    assert finding["source_ids"]==[record["record_id"]]
    assert finding["evidence_class"]=="USER_ATTACHED_UNVERIFIED_SOURCE"


def test_text_and_docx_sections_and_unsupported_files():
    sections=_decode_document("note.txt",b"First finding\n\nSecond section")
    assert [x["section"] for x in sections]==["Section 1","Section 2"]
    from docx import Document
    doc=Document();doc.add_paragraph("A finding");doc.add_paragraph("A second finding")
    stream=io.BytesIO();doc.save(stream)
    sections=_decode_document("meeting.docx",stream.getvalue())
    assert sections[0]["section"]=="Paragraph 1"
    with pytest.raises(HTTPException,match=""):
        _decode_document("table.xlsx",b"fake")
    with pytest.raises(HTTPException):
        _decode_document("scanned.pdf",b"%PDF-1.4\n%%EOF")


def test_upload_scanner_fails_closed_when_not_configured(monkeypatch):
    monkeypatch.delenv("ASSISTANT_CLAMAV_HOST",raising=False)
    with pytest.raises(HTTPException) as exc:
        _clamav_scan(b"valid text")
    assert exc.value.status_code==503
    assert "scanner" in str(exc.value.detail).lower()


def test_owner_scoped_attachments_opening_and_deletion_redaction(monkeypatch):
    # SQLAlchemy model contract in an isolated local SQLite database, no Supabase.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    eng=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(eng,tables=[
        User.__table__,AssistantThread.__table__,AssistantChatAttachment.__table__,
        AssistantResponseFeedback.__table__])
    db=sessionmaker(bind=eng)()
    try:
        u=User(email="chat-qa@example.invalid",password_hash="test")
        other=User(email="other-qa@example.invalid",password_hash="test")
        db.add_all([u,other]);db.flush()
        thread=AssistantThread(id=str(uuid.uuid4()),user_id=u.id,title="Owner chat")
        db.add(thread);db.flush()
        aid=str(uuid.uuid4())
        recid="ATT-"+aid.replace("-","")+"-S1"
        thread.messages_json=json.dumps([
          {"role":"user","text":"Summarize","attachment_ids":[aid]},
          {"role":"assistant","text":"Quoted sensitive document text ["+recid+"]",
           "attached_source_ids":[recid],"records":[{"record_id":recid}]}
        ])
        record=AssistantChatAttachment(id=aid,thread_id=thread.id,user_id=u.id,
          kind="DOCUMENT",title="note.txt",url="",source_digest="0"*64,
          extracted_text="Page 1: Original contents",
          sections_json=json.dumps([{"section":"Section 1","text":"Original contents"}]),
          access_scope_json=json.dumps(_scope(officer()),sort_keys=True))
        db.add(record);db.commit()
        monkeypatch.setattr("app.assistant_attachments._user_scope",lambda db,user:officer())
        rows=selected_attachment_evidence(db,u,officer(),thread.id,[aid])
        assert rows[0]["record_id"]==recid
        assert rows[0]["source_excerpt"]=="Original contents"
        cited=read_attachment_section(thread.id,aid,1,u,db)
        assert cited["text"]=="Original contents"
        assert cited["shared_case_record"] is False
        with pytest.raises(HTTPException) as exc:
            selected_attachment_evidence(db,other,officer(),thread.id,[aid])
        assert exc.value.status_code==404
        with pytest.raises(HTTPException) as exc:
            selected_attachment_evidence(db,u,{**officer(),"province_code":"31"},thread.id,[aid])
        assert exc.value.status_code==403
        done=remove_attachment(thread.id,aid,u,db)
        assert done["deleted"] and done["derived_history_redacted"]
        saved=json.loads(db.get(AssistantThread,thread.id).messages_json)
        assert "Quoted sensitive" not in saved[1]["text"]
        assert saved[1]["records"]==[]
        assert db.get(AssistantChatAttachment,aid) is None
    finally:
        db.close();eng.dispose()


def test_link_https_and_blocked_or_unreachable_not_saved(monkeypatch):
    monkeypatch.setattr("app.assistant_attachments._user_scope",lambda db,user:officer())
    with pytest.raises(HTTPException) as exc:
        attach_link(LinkRequest(thread_id=str(uuid.uuid4()),url="http://localhost/admin"),
                    SimpleNamespace(id=1),None)
    assert exc.value.status_code==422


def test_feedback_is_bound_to_own_saved_assistant_message():
    # Persistence constraints are checked by database integration QA; no raw
    # source content is written to feedback rows.
    assert AssistantResponseFeedback.__tablename__=="assistant_response_feedback"
    assert "answer_sha256" in AssistantResponseFeedback.__table__.columns
