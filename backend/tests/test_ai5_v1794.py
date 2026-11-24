"""AI-5 v179.4: deterministic tests of source isolation, conversational
mode-switching, attachment security, real exports and failure recovery.
All news/source claims are synthetic fixtures; no paid model calls.
"""
import io
import uuid
import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from app.ai5 import api,engine,state,export,web
from app.ai4 import attachments as storage

OFFICER={"role":"Regency/City Officer","status":"Active","geographic_scope":"Regency/City",
         "province":"Jawa Barat","regency_city":"Bandung",
         "permissions":{"view_intelligence":True}}
LEADER={**OFFICER,"role":"National Leadership","geographic_scope":"Nationwide"}


@pytest.fixture(autouse=True)
def clean():
    storage.STORES.clear()
    yield
    storage.STORES.clear()


def cid():return str(uuid.uuid4())


def user(id=3):return type("User",(),{"id":id})()


def source(kind="PUBLIC_REPORT",id="WEB-AAA-1",status="READ"):
    return {"id":id,"title":"Synthetic published source","type":kind,
            "read_status":status,
            "basis":"LIVE_PUBLIC_LOOKUP" if kind.startswith("PUBLIC_") else
                    "FIXED_SAVED_SNAPSHOT" if kind.startswith("SAVED_") else "OFFICER_UPLOADED_UNVERIFIED",
            "url":"https://example.org/synthetic-article" if kind.startswith("PUBLIC_") else "",
            "excerpt":"Source passage provided in an isolated test. Not a real current article.",
            "published_at":"2026-11-20","updated_at":"","duplicate_of":"","section":""}


def payload(ids=None,draft=""):
    ids=ids if ids is not None else ["WEB-AAA-1"]
    return {"title":"Research findings",
      "body":"The findings are provisional. "+" ".join("[["+x+"]]" for x in ids),
      "draft":draft,
      "table":{"title":"Options","columns":["Option","Trade-off"],
               "rows":[["Verify", "Review effort"],["Monitor","May delay response"]]},
      "open_questions":["Does the new source supersede an earlier result?"],
      "source_ids":ids}


def mock_access(monkeypatch,grant=LEADER):
    monkeypatch.setattr(api,"profile",lambda db,u:grant)
    monkeypatch.setattr(api,"has",lambda *args:True)


def no_network(monkeypatch):
    monkeypatch.setattr(api.web,"research",lambda *a:{
        "status":"NO_READABLE_PAGES","sources":[],"as_of":"2026-11-24T00:00:00Z","attempts":[]})


def test_general_default_without_forced_bawaslu_prompt():
    cfg=engine.validate({"question":"Explain a rainbow to my child"},OFFICER)
    assert cfg["mode"]=="GENERAL_RESEARCH"
    assert cfg["source_mode"]=="WEB_ONLY"
    assert "ANY" in engine.SYSTEM and "Do NOT force election" in engine.SYSTEM
    assert cfg["action_mode"]=="OPERATIONAL"
    for mode in ("WEB_ONLY","WEB_SMARTRADAR","SMARTRADAR_ONLY"):
        for action in ("GENERAL_RESEARCH","BAWASLU_ACTION"):
            c=engine.validate({"question":"Explain gravity","mode":action,
                               "sourceMode":mode},OFFICER)
            assert c["source_mode"]==mode
    with pytest.raises(HTTPException) as ex:
        engine.validate({"question":"Decision options","mode":"BAWASLU_ACTION",
                         "actionMode":"MANAGEMENT"},OFFICER)
    assert ex.value.status_code==403
    assert engine.validate({"question":"Decision options","mode":"BAWASLU_ACTION",
                             "actionMode":"MANAGEMENT"},LEADER)["action_mode"]=="MANAGEMENT"


def test_web_only_never_loads_internal_records_including_mode_switch(monkeypatch):
    mock_access(monkeypatch)
    no_network(monkeypatch)
    monkeypatch.setattr(api,"saved_research",lambda *args:(_ for _ in ()).throw(AssertionError("Private retrieval blocked")))
    monkeypatch.setattr(api.engine,"generate",lambda cfg,hist,src,*args:(payload([]),"COMPLETE"))
    conversation=cid()
    op=api.chat({"question":"Explain how to measure rainfall","conversationId":conversation,
                 "sourceMode":"WEB_ONLY"},user(),object())
    assert op["mode"]=="GENERAL_RESEARCH"
    assert op["research_trail"]["saved_count"]==0
    applied=api.chat({"question":"How does this apply to my office?",
                      "mode":"BAWASLU_ACTION","actionMode":"OPERATIONAL",
                      "sourceMode":"WEB_ONLY","conversationId":conversation},user(),object())
    assert applied["mode"]=="BAWASLU_ACTION"
    assert applied["conversation_id"]==conversation
    back=api.chat({"question":"What about cloud seeding instead?",
                   "mode":"GENERAL_RESEARCH","sourceMode":"WEB_ONLY",
                   "conversationId":conversation},user(),object())
    assert back["mode"]=="GENERAL_RESEARCH"
    assert len(state.turns(user(),conversation,LEADER))==3


def test_mixed_mode_uses_public_then_authorised_and_filters_on_switch(monkeypatch):
    mock_access(monkeypatch)
    calls=[]
    published=source()
    saved=source("SAVED_SOCIAL","SOCIAL-740","SAVED_SNAPSHOT")
    monkeypatch.setattr(api.web,"research",lambda *a:(calls.append("web") or
                         {"status":"READ_SOURCES_AVAILABLE","sources":[published],
                          "as_of":"2026-11-24","attempts":[]}))
    monkeypatch.setattr(api,"saved_research",lambda *a:(calls.append("saved") or ([saved],[])))
    model_context=[]
    def model(cfg,hist,src,*args):
        model_context.append({"source_mode":cfg["source_mode"],"history":hist,
                              "source_types":[s["type"] for s in src]})
        return payload(["WEB-AAA-1"]),"COMPLETE"
    monkeypatch.setattr(api.engine,"generate",model)
    conversation=cid()
    mixed=api.chat({"question":"Compare public and internal oversight leads",
                    "conversationId":conversation,"sourceMode":"WEB_SMARTRADAR"},user(),object())
    assert calls==["web","saved"]
    assert mixed["research_trail"]["saved_count"]==1
    calls.clear()
    web_only=api.chat({"question":"Shorten this explanation",
                       "conversationId":conversation,"sourceMode":"WEB_ONLY"},user(),object())
    assert calls==[]
    assert any("Earlier material is unavailable" in warning
               for warning in web_only["research_trail"]["warnings"])
    assert web_only["research_trail"]["saved_count"]==0
    assert "SAVED_SOCIAL" not in model_context[-1]["source_types"]
    assert all("SAVED_SOCIAL" not in str(x) for x in model_context[-1]["history"])
    with pytest.raises(HTTPException) as exc:
        api.chat({"question":"Rewrite previous","sourceMode":"WEB_ONLY",
                  "referenceTurnId":mixed["turn_id"],"conversationId":conversation},user(),object())
    assert exc.value.status_code==409


def test_citations_are_eligible_only():
    cfg=engine.validate({"question":"Compare sources"},LEADER)
    rows=[source(),source("PUBLIC_REPORT","WEB-B-2","SNIPPET_ONLY")]
    raw=payload(["WEB-AAA-1","WEB-B-2","FAKE-9"])
    result=engine.sanitize(raw,rows,cfg,"READ_SOURCES_AVAILABLE")
    assert "[[WEB-AAA-1]]" in result["body"]
    assert "[[WEB-B-2]]" not in result["body"]
    assert "[[FAKE-9]]" not in result["body"]
    assert result["source_ids"]==["WEB-AAA-1"]


def test_new_topic_searches_while_rewrites_reuse_prior():
    cfg=engine.validate({"question":"Any updates about a different topic?"},LEADER)
    assert api.needs_tools(cfg,{"question":"Earlier topic"},[]) is True
    cfg["question"]="Shorten the earlier draft"
    assert api.needs_tools(cfg,{"question":"Earlier topic"},[]) is False
    cfg["question"]="How does this apply to my office?"
    assert api.needs_tools(cfg,{"question":"Earlier topic"},[]) is False
    cfg["question"]="What does this PDF say?"
    assert api.needs_tools(cfg,None,[source("ATTACHMENT_PDF","FILE-TEST-1")]) is False


def test_attachments_isolate_owner_and_followup_and_removal():
    conversation=cid()
    u=user()
    item=state.add_file(u,conversation,LEADER,"findings.txt",
                         b"One observation.\n\nSecond observation.")
    assert item["status"]=="READY"
    assert item["sections_count"]==2
    assert not state.attachments_for(user(99),conversation,LEADER)
    before=state.attachments_for(u,conversation,LEADER)
    assert all("findings.txt" in r["title"] for r in before)
    state.remove_file(u,conversation,LEADER,item["id"])
    assert not state.attachments_for(u,conversation,LEADER)


def test_access_change_revokes_previous_conversation():
    conversation=cid()
    state.conversation(user(),conversation,LEADER,True)
    changed={**LEADER,"role":"Provincial Officer"}
    with pytest.raises(HTTPException) as ex:
        state.conversation(user(),conversation,changed,False)
    assert ex.value.status_code==403


def test_export_bytes_are_valid_pdf_editable_docx_and_structured_xlsx():
    turn={"turn_id":"1"*32,"question":"Compare options","mode":"GENERAL_RESEARCH",
          "source_mode":"WEB_ONLY",
          "answer":engine.sanitize(payload(),[source()],
                      engine.validate({"question":"Compare options"},LEADER),
                      "READ_SOURCES_AVAILABLE"),
          "sources":[source()]}
    for ext,signature in (("pdf",b"%PDF-"),("docx",b"PK"),("xlsx",b"PK")):
        contents,mime,filename=export.create(turn,ext)
        assert contents.startswith(signature)
        assert filename.endswith("."+ext)
        assert len(contents)>700
        if ext=="pdf":
            reader=PdfReader(io.BytesIO(contents))
            assert len(reader.pages)>=1
            assert "Research" in (reader.pages[0].extract_text() or "")
        elif ext=="docx":
            doc=Document(io.BytesIO(contents))
            assert doc.tables and doc.tables[0].cell(1,0).text=="Verify"
        else:
            book=load_workbook(io.BytesIO(contents))
            assert book["Analysis"].cell(2,1).value=="Verify"
            assert book["Sources"].max_row>=2
            assert "Context and caveats" in book.sheetnames


def test_xlsx_formula_like_text_is_safely_escaped():
    assert export._literal("=1+1").startswith("'")
    assert export._literal("  @malicious").startswith("'")
    assert export._literal("Plain content")=="Plain content"


def test_export_failure_does_not_remove_answer(monkeypatch):
    mock_access(monkeypatch)
    no_network(monkeypatch)
    monkeypatch.setattr(api.engine,"generate",lambda *a:(payload([]),"COMPLETE"))
    conversation=cid()
    chat=api.chat({"question":"Compare two risks","conversationId":conversation},
                  user(),object())
    def fail(*args):raise RuntimeError("controlled file error")
    monkeypatch.setattr(api.export,"create",fail)
    with pytest.raises(HTTPException) as err:
        api.download("pdf",{"conversationId":conversation,
                "turnId":chat["turn_id"],"sourceMode":"WEB_ONLY"},user(),object())
    assert err.value.status_code==503
    assert state.get_turn(user(),conversation,LEADER,chat["turn_id"])["answer"]["body"]


def test_export_for_removed_file_is_rejected(monkeypatch):
    mock_access(monkeypatch)
    monkeypatch.setattr(api.engine,"generate",lambda *a:(payload([]),"COMPLETE"))
    conversation=cid()
    attached=state.add_file(user(),conversation,LEADER,"case.txt",b"Redacted note")
    row=api.chat({"question":"Summarise the attached file","conversationId":conversation},
                user(),object())
    state.remove_file(user(),conversation,LEADER,attached["id"])
    with pytest.raises(HTTPException) as err:
        api.download("xlsx",{"conversationId":conversation,
                "turnId":row["turn_id"],"sourceMode":"WEB_ONLY"},user(),object())
    assert err.value.status_code==409


def test_web_model_discovery_is_general_topic_and_uses_read_sources(monkeypatch):
    calls=[]
    def discover(question,key,model,base,as_of,newest):
        calls.append(newest)
        return {"status":"FOUND","rows":[{"url":"https://example.org/info",
            "title":"Synthetic science information","snippet":""}]}
    monkeypatch.setattr(web,"discover",discover)
    monkeypatch.setattr(web,"read_page",lambda row:{
        **source(),"url":row["url"],"title":row["title"],"read_status":"READ"})
    r=web.research("Latest scientific report", "provider-key","model",
                   "https://api.openai.com/v1","2026-11-24")
    assert calls.count(True)==1
    # Searches run concurrently; one discovery and one freshness lookup are
    # required, plus at most one targeted gap follow-up if coverage is unclear.
    assert 1<=calls.count(False)<=2
    if len(calls)==3:
        assert r["attempts"][-1]["phase"]=="gap follow-up"
    assert r["read_count"]==1
    assert r["sources"][0]["id"].startswith("WEB-")


def test_unapproved_management_mode_rejected_at_api(monkeypatch):
    mock_access(monkeypatch,OFFICER)
    with pytest.raises(HTTPException) as exc:
        api.chat({"question":"What should leadership decide?",
                 "mode":"BAWASLU_ACTION","actionMode":"MANAGEMENT",
                 "conversationId":cid()},user(),object())
    assert exc.value.status_code==403


def test_edited_draft_carries_into_followup_with_open_questions(monkeypatch):
    mock_access(monkeypatch)
    no_network(monkeypatch)
    observed=[]
    def model(cfg,hist,*args):
        observed.append(hist)
        return payload([],"DRAFT original memo"),"COMPLETE"
    monkeypatch.setattr(api.engine,"generate",model)
    conversation=cid()
    first=api.chat({"question":"Draft an example memo","conversationId":conversation},user(),object())
    next_turn=api.chat({"question":"Shorten the earlier draft",
        "conversationId":conversation,
        "referenceTurnId":first["turn_id"],
        "editedDraft":"REVIEWER EDIT: preserve evidence caveats"},user(),object())
    assert next_turn["conversation_id"]==conversation
    assert observed[-1][-1]["draft"]=="REVIEWER EDIT: preserve evidence caveats"
    assert any("Open questions" in str(item) or item.get("open_questions")
               for item in observed[-1][:-1])
