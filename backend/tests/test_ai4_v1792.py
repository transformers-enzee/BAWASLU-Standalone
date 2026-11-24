"""AI-4 isolated contract, source, attachment and follow-up acceptance tests.

No paid search/model calls, no existing assistant mutation and no real
official sources are represented by these controlled fixtures.
"""
import uuid
import pytest
from fastapi import HTTPException
from app.ai4 import api,attachments,core
from app.unified_ai import web as web_reader

OFFICER={"role":"Regency/City Officer","status":"Active","geographic_scope":"Regency/City",
         "province":"Jawa Barat","regency_city":"Bandung",
         "permissions":{"view_intelligence":True}}
LEADER={**OFFICER,"role":"National Leadership","geographic_scope":"Nationwide"}


@pytest.fixture(autouse=True)
def clean_sessions():
    attachments.STORES.clear()
    yield
    attachments.STORES.clear()


def cid():return str(uuid.uuid4())


def fake_source(name="WEB-1"):
    return {"id":name,"type":"PUBLIC_OFFICIAL","title":"Synthetic public official page",
            "read_status":"READ","basis":"LIVE_PUBLIC_LOOKUP",
            "url":"https://bawaslu.go.id/synthetic-not-real",
            "published_at":"2026-11-24","updated_at":"","duplicate_of":"",
            "excerpt":"Synthetic notice for isolated test",
            "location_verified":False,"reason":"Controlled fixture"}


def fake_answer():
    return {"lead":"Your office should verify the original announcement first.",
            "findings":[{"text":"The synthetic notice is a reported public page.",
                         "source_ids":["WEB-1","INVENTED"]}],
            "comparison":[{"option":"Verify","benefit":"Reliable dates","tradeoff":"Review effort",
                           "responsible_role":"BAWASLU legal reviewer","timeframe":"Proposed week one",
                           "source_ids":["WEB-1"]}],
            "next_steps":[{"action":"Check jurisdiction","owner_role":"Legal reviewer",
                           "review_point":"Before any filing","source_ids":["WEB-1"]}],
            "uncertainties":["Current legal instrument needs verification"],
            "clarifying_question":"","draft":"DRAFT: Bawaslu staff to review."}


def test_roles_and_source_selection():
    assert core.validate({"question":"Apa yang perlu diverifikasi?"},OFFICER)["source_mode"]=="WEB_ONLY"
    assert core.source_preferences("WEB_ONLY")=={
        "publicWeb":True,"smartRadar":False,"legalReferences":False}
    assert core.validate({"question":"Assess","workspace":"MANAGEMENT"},LEADER)["workspace"]=="MANAGEMENT"
    with pytest.raises(HTTPException) as e:
        core.validate({"question":"Assess","workspace":"MANAGEMENT"},OFFICER)
    assert e.value.status_code==403
    assert core.profile_context(OFFICER)["office_level"]=="BAWASLU kabupaten/kota"
    for p in ("AUTO","EXECUTIVE","OPERATIONAL","RESEARCH"):
        assert core.validate({"question":"Assess","perspective":p},OFFICER)["perspective"]==p


def test_web_only_never_invokes_saved_record_retrieval_even_when_search_fails(monkeypatch):
    calls=[]
    monkeypatch.setattr(api,"profile",lambda db,user:OFFICER)
    monkeypatch.setattr(api,"has",lambda grant,key:True)
    monkeypatch.setattr(api,"authorised_records",lambda *a:(_ for _ in ()).throw(AssertionError("Saved records forbidden")))
    def lookup(*args):
        calls.append("web")
        return {"status":"PROVIDER_HTTP_403","sources":[],"as_of":"now",
                "queries":[],"attempts":[]}
    monkeypatch.setattr(api,"search_public_web",lookup)
    def synthesis(cfg,scope,public,saved,uploads,*args):
        calls.append("model")
        assert saved==[] and uploads==[]
        return fake_answer(),"COMPLETE"
    monkeypatch.setattr(api,"synthesis",synthesis)
    monkeypatch.setenv("OPENAI_API_KEY","fake-key")
    identity=cid()
    result=api.chat({"question":"Latest public news","conversationId":identity,
                     "sourceMode":"WEB_ONLY"},type("U",(),{"id":11})(),object())
    assert calls==["web","model"]
    assert result["source_trail"]["saved_count"]==0
    assert result["source_trail"]["public_status"]=="PROVIDER_HTTP_403"
    assert result["answer"]["findings"]==[]


def test_model_citations_are_checked_against_actually_read_sources():
    cfg=core.validate({"question":"Explain a source"},OFFICER)
    result=core.sanitize(fake_answer(),[fake_source()],cfg,"READ_SOURCES_AVAILABLE")
    assert result["findings"][0]["source_ids"]==["WEB-1"]
    assert result["next_steps"][0]["source_ids"]==["WEB-1"]
    snippet=fake_source()
    snippet["read_status"]="SNIPPET_ONLY"
    no=core.sanitize(fake_answer(),[snippet],cfg,"SNIPPET_ONLY")
    assert no["findings"]==[]


def test_current_news_without_readable_source_discloses_failure():
    cfg=core.validate({"question":"Latest election news today"},OFFICER)
    result=core.sanitize(fake_answer(),[],cfg,"NO_READABLE_PUBLIC_PAGES")
    assert result["findings"]==[]
    assert result["draft"]==""
    assert "No readable source" in result["lead"]


def test_mixed_mode_follows_web_first_and_keeps_public_separate(monkeypatch):
    calls=[]
    monkeypatch.setattr(api,"profile",lambda *a:LEADER)
    monkeypatch.setattr(api,"has",lambda *a:True)
    monkeypatch.setenv("OPENAI_API_KEY","fake-key")
    public=fake_source()
    saved={**fake_source("SOCIAL-740"),"type":"SAVED_SOCIAL","basis":"FIXED_SAVED_SNAPSHOT",
           "read_status":"SAVED_SNAPSHOT","url":"","excerpt":"Unverified social post"}
    def search(*args):
        calls.append("web");return {"status":"READ_SOURCES_AVAILABLE","sources":[public],
                                    "as_of":"now","queries":[],"attempts":[]}
    def records(*args):
        calls.append("saved");return [saved],[]
    monkeypatch.setattr(api,"search_public_web",search)
    monkeypatch.setattr(api,"authorised_records",records)
    monkeypatch.setattr(api,"synthesis",lambda *a:(fake_answer(),"COMPLETE"))
    r=api.chat({"question":"Compare public and saved information",
                "sourceMode":"WEB_SMARTRADAR","workspace":"MANAGEMENT",
                "conversationId":cid()},type("U",(),{"id":11})(),object())
    assert calls==["web","saved"]
    assert r["source_trail"]["read_public_count"]==1
    assert r["source_trail"]["saved_count"]==1
    assert r["workspace"]=="MANAGEMENT"


def test_txt_attachment_survives_followups_and_removal(monkeypatch):
    ident=cid()
    file=attachments.add_file(11,ident,OFFICER,"evidence.txt",
                              b"Source detail A\n\nSource detail B")
    assert file["status"]=="READY"
    assert file["sections_count"]==2
    sources=attachments.evidence(11,ident,OFFICER)
    assert len(sources)==2
    assert all("evidence.txt" in s["title"] for s in sources)
    state=attachments.bind_mode(11,ident,OFFICER,"WEB_ONLY")
    assert state["mode"]=="WEB_ONLY"
    assert len(attachments.evidence(11,ident,OFFICER))==2
    attachments.remove(11,ident,OFFICER,file["id"])
    assert attachments.evidence(11,ident,OFFICER)==[]


def test_attachments_isolated_to_user_scope_and_mode():
    ident=cid()
    attachments.add_file(11,ident,OFFICER,"case.txt",b"Example text")
    assert attachments.evidence(12,ident,OFFICER)==[]
    changed={**OFFICER,"province_code":"OTHER"}
    with pytest.raises(HTTPException) as denied:
        attachments.evidence(11,ident,changed)
    assert denied.value.status_code==403
    other=cid()
    attachments.bind_mode(11,other,OFFICER,"WEB_ONLY")
    with pytest.raises(HTTPException) as wrong:
        attachments.bind_mode(11,other,OFFICER,"SMARTRADAR_ONLY")
    assert wrong.value.status_code==409


def test_file_safety_and_link_restrictions(monkeypatch):
    for filename,data in (("x.pdf",b"not-a-pdf"),("x.docx",b"fake"),
                          ("x.exe",b"binary"),("x.txt",b"\x00binary")):
        with pytest.raises(HTTPException):attachments.file_sections(filename,data)
    with pytest.raises(HTTPException):attachments.file_sections("big.txt",b"a"*(5*1024*1024+1))
    for url in ("http://bawaslu.go.id/","https://127.0.0.1/admin",
                "https://localhost:8000/","https://10.0.0.1/internal"):
        with pytest.raises(HTTPException):
            attachments.add_link(1,cid(),OFFICER,url)
    def opened(s):
        return {"url":s["url"],"resolved_url":s["url"],"title":"Synthetic link",
                "excerpt":"Synthetic test link content with evidence.", "read_status":"READ",
                "published_at":"2026-11-24","updated_at":""}
    monkeypatch.setattr(attachments,"read_page",opened)
    row=attachments.add_link(11,cid(),OFFICER,"https://bawaslu.go.id/test")
    assert row["kind"]=="LINK"


def test_file_extraction_pdf_or_docx_sections():
    from docx import Document
    import io
    d=Document()
    d.add_heading("Official records for review",1)
    d.add_paragraph("A fictional case note to be verified.")
    f=io.BytesIO();d.save(f)
    name,sections,truncated=attachments.file_sections("review.docx",f.getvalue())
    assert name=="review.docx"
    assert any("paragraph" in s["section"] for s in sections)
    assert truncated is False


def test_unavailable_public_search_never_switches_to_saved_records(monkeypatch):
    monkeypatch.setattr(api,"profile",lambda *a:LEADER)
    monkeypatch.setattr(api,"has",lambda *a:True)
    monkeypatch.setattr(api,"authorised_records",lambda *a:(_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(api,"search_public_web",lambda *a:{
        "status":"PROVIDER_NOT_CONFIGURED","sources":[],"queries":[],"attempts":[]})
    monkeypatch.setattr(api,"synthesis",lambda *a:(None,"SYNTHESIS_NOT_CONFIGURED"))
    out=api.chat({"question":"What changed this week?","sourceMode":"WEB_ONLY",
                  "conversationId":cid()},type("U",(),{"id":7})(),object())
    assert out["source_trail"]["saved_count"]==0
    assert "PROVIDER_NOT_CONFIGURED" in " ".join(out["source_trail"]["warnings"])


def test_feedback_is_permissioned_and_ephemeral(monkeypatch):
    monkeypatch.setattr(api,"profile",lambda *a:OFFICER)
    monkeypatch.setattr(api,"has",lambda *a:True)
    ident=cid()
    attachments.bind_mode(11,ident,OFFICER,"WEB_ONLY")
    user=type("U",(),{"id":11})()
    row=api.feedback({"conversation_id":ident,"turn_id":"a"*32,
        "clarity":5,"source_quality":3,"usefulness":4,"note":"Readable"},user,object())
    assert row["saved"] is True
    assert api.list_feedback(ident,user,object())["feedback"][0]["usefulness"]==4
    with pytest.raises(HTTPException):
        api.feedback({"conversation_id":ident,"turn_id":"a"*32,
            "clarity":0,"source_quality":3,"usefulness":4,"note":""},user,object())
