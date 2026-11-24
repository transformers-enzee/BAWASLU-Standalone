"""Rebuilt unified AI Assistant v179.1: isolated no-network acceptance.

Tests actual handler routing, sourcing gates and source allowlist; no paid
provider calls or claim that Bryan/Grace have personally conducted UAT.
"""
from datetime import date
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.unified_ai import api,web
from app.unified_ai.contract import validate,window,local_today,jurisdiction,safe_for_public
from app.unified_ai.answer import safe_answer,model_context,eligible,provenance
from app.unified_ai.saved import dedupe

LEADER={"role":"National Leadership","status":"Active","geographic_scope":"Nationwide",
    "province":"","regency_city":"","permissions":{"view_intelligence":True}}
OFFICER={"role":"Regency/City Officer","status":"Active","geographic_scope":"Regency/City",
    "province":"Jawa Barat","regency_city":"Bandung","permissions":{"view_intelligence":True}}

def request(question="What is the latest official oversight guidance?",**kwargs):
    return {"question":question,**kwargs}

def source(id,typ="PUBLIC_OFFICIAL",status="READ",when="2026-11-24",text="Source content"):
    return {"id":id,"type":typ,"title":"Publication "+id,
        "url":"https://bawaslu.go.id/article/"+id,"resolved_url":"",
        "published_at":when,"updated_at":"","read_status":status,
        "basis":"LIVE_PUBLIC_LOOKUP" if typ.startswith("PUBLIC") else "FIXED_SAVED_SNAPSHOT",
        "excerpt":text,"reliability":"SAVED_SOCIAL_UNVERIFIED" if typ=="SAVED_SOCIAL" else
          "OFFICIAL_PUBLICATION_UNVERIFIED","reason":"","location_verified":False,
        "location":"","duplicate_of":""}

def raw(ids):
    return {"lead":"The latest official update requires verification.",
        "attention":"WATCH","confidence":"MODERATE","first_step":"Verify the latest original notice.",
        "what_changed":"Updated date appears in the newer publication.",
        "why_it_matters":"Potential change in the procedural review timetable.",
        "geographic_implications":"Incident province remains unverified.",
        "institutional_implications":"Authority needs a legal reviewer.",
        "recommendation":"Recommend a conditional source review.",
        "findings":[{"claim":"The newer notice updates the older publication.",
                      "source_ids":ids,"uncertainty":"Currentness must be checked."}],
        "options":[{"title":"Review","benefit":"Establish dates","tradeoff":"Staff effort",
                    "reason":"Proportionate","source_ids":ids}],
        "plan":[{"task":"Verify original publication","owner_role":"Authorised legal reviewer",
                 "milestone":"Proposed week 1","review_point":"Leadership checkpoint",
                 "evidence_needed":"Original dated document","decision_gate":"Escalate only if verified",
                 "source_ids":ids}],
        "legal_checks":["Check controlling instrument and jurisdiction"],
        "watch_next":["New official corrections"],"uncertainties":["No complete national population"],
        "draft":"DRAFT MEMO — officer review only"}

def test_workspace_perspective_and_officer_level_are_separate():
    assert validate(request(),OFFICER)["workspace"]=="OPERATIONAL"
    assert validate(request(sourceMode="WEB_ONLY"),OFFICER)["sources"]=={
        "publicWeb":True,"smartRadar":False,"legalReferences":False}
    assert validate(request(workspace="MANAGEMENT",perspective="OPERATIONAL"),LEADER)["workspace"]=="MANAGEMENT"
    with pytest.raises(HTTPException) as denied:
        validate(request(workspace="MANAGEMENT"),OFFICER)
    assert denied.value.status_code==403
    assert jurisdiction(OFFICER)["office_level"]=="BAWASLU kabupaten/kota"
    assert jurisdiction(LEADER)["office_level"]=="BAWASLU RI"
    for perspective in ("AUTO","EXECUTIVE","OPERATIONAL","RESEARCH"):
        assert validate(request(perspective=perspective),LEADER)["perspective"]==perspective

def test_explicit_recency_calendar_in_indonesia():
    assert window("What changed in the past 2 weeks?",date(2026,11,24))=={
        "start":"2026-11-11","end":"2026-11-24","kind":"EXPLICIT_RECENT","days":14}
    assert window("Tren 2 minggu terakhir",date(2026,11,24))["start"]=="2026-11-11"
    assert window("20 days ago",date(2026,11,24)) is None

def test_private_ids_cannot_be_forwarded_to_public_discovery():
    for q in ("Compare SOCIAL-740 and SOCIAL-1160","Investigate INT-2026-11",
              "See DOC-2-P1","Email user@example.com"):
        assert not safe_for_public(q)
    assert safe_for_public("Find a BAWASLU announcement in the public press")

def test_private_mode_does_not_return_any_internal_records_even_on_web_failure(monkeypatch):
    calls=[]
    monkeypatch.setattr(api,"profile",lambda db,user:LEADER)
    monkeypatch.setattr(api,"has",lambda grant,permission:True)
    def public(question,cfg,*args):
        calls.append("web")
        assert cfg["source_mode"]=="WEB_ONLY"
        return {"status":"PROVIDER_HTTP_403","sources":[],"queries":[],"as_of":"now","attempts":[]}
    monkeypatch.setattr(api,"public_research",public)
    monkeypatch.setattr(api,"saved_research",lambda *a:(_ for _ in ()).throw(AssertionError("Private retrieval forbidden")))
    def llm(cfg,context,*args):
        calls.append("model")
        assert context["source_mode"]=="WEB_ONLY"
        assert context["sources"]==[]
        return raw([]),"COMPLETE"
    monkeypatch.setattr(api,"request_ai",llm)
    monkeypatch.setenv("OPENAI_API_KEY","synthetic-test-key")
    result=api.chat(request(),object(),object())
    assert calls==["web","model"]
    assert result["sources"]==[]
    assert result["answer"]["findings"]==[]
    assert result["answer"]["lead"].startswith("Live public research returned no readable pages")
    assert result["public_research"]["status"]=="PROVIDER_HTTP_403"

def test_mixed_mode_uses_public_first_and_separate_unverified_social(monkeypatch):
    calls=[]
    monkeypatch.setattr(api,"profile",lambda db,user:LEADER)
    monkeypatch.setattr(api,"has",lambda *args:True)
    news=source("WEB-1",when="2026-11-24",text="New official guidance issued.")
    social=source("SOCIAL-740","SAVED_SOCIAL","SAVED_SNAPSHOT","2026-11-23",
                  "A fictional post alleges an unverified document problem")
    def public(*args):
        calls.append("public")
        return {"status":"READ_SOURCES_AVAILABLE","sources":[news],"queries":["official news"],
                "as_of":"now","attempts":[]}
    def saved(*args):
        calls.append("saved")
        return [social],[]
    monkeypatch.setattr(api,"public_research",public)
    monkeypatch.setattr(api,"saved_research",saved)
    monkeypatch.setattr(api,"request_ai",lambda cfg,context,*rest:(raw(["WEB-1","SOCIAL-740"]),"COMPLETE"))
    monkeypatch.setenv("OPENAI_API_KEY","synthetic-test-key")
    result=api.chat(request(sourceMode="WEB_SMARTRADAR"),object(),object())
    assert calls==["public","saved"]
    assert [x["type"] for x in result["sources"]]==["PUBLIC_OFFICIAL","SAVED_SOCIAL"]
    assert result["answer"]["findings"][0]["evidence_class"]=="ATTRIBUTED_SAVED_ALLEGATION_UNVERIFIED"
    assert result["source_consultation"][1]["status"]=="CONSULTED"
    assert result["source_consultation"][0]["read_count"]==1

def test_unread_snippet_does_not_support_a_claim():
    snippet=source("WEB-2","PUBLIC_REPORT","SNIPPET_ONLY")
    old=source("WEB-3","PUBLIC_OFFICIAL","READ","2026-11-05")
    new=source("WEB-1","PUBLIC_OFFICIAL","READ","2026-11-24")
    cfg=validate(request("What changed in the past 2 weeks?"),LEADER)
    cfg["window"]=window(cfg["question"],date(2026,11,24))
    for row in (old,new):
        row["within_period"]=row["published_at"]>=cfg["window"]["start"]
    x=safe_answer(raw(["WEB-1","WEB-2","WEB-3"]),[snippet,old,new],cfg,"READ_SOURCES_AVAILABLE")
    assert x["findings"][0]["source_ids"]==["WEB-1"]
    assert "WEB-2" not in x["findings"][0]["source_ids"]
    assert "WEB-3" not in x["findings"][0]["source_ids"]
    assert provenance(["WEB-1"],{"WEB-1":new})=="READ_OFFICIAL_PUBLICATION_NOT_OFFICER_AUTHENTICATED"

def test_deduplication_does_not_count_reposts_as_independent_cases():
    s1=source("SOCIAL-740","SAVED_SOCIAL","SAVED_SNAPSHOT")
    s2=source("SOCIAL-1160","SAVED_SOCIAL","SAVED_SNAPSHOT")
    s2["url"]=s1["url"]+"?utm_source=copy"
    rows=dedupe([s1,s2])
    assert rows[1]["duplicate_of"]=="SOCIAL-740"
    assert eligible(rows[0])
    assert not eligible(rows[1])

def test_public_reader_rejects_local_and_insecure_urls():
    for url in ("http://bawaslu.go.id/notice","https://localhost/internal",
                "https://127.0.0.1/local","https://10.0.0.1/records",
                "https://evil.test@localhost/private"):
        assert not web.safe_url(url)
    assert web.safe_url("https://jdih.bawaslu.go.id/peraturan")

def test_html_parser_provides_actual_title_and_publication_date():
    data=('''<html><head><meta property="article:published_time" content="2026-11-24T08:00:00+07:00">
             <title>Officially revised schedule</title></head><body><article><p>'''
          +("The authority published an updated official timetable replacing the older published notice. "*8)+
          '''</p></article></body></html>''').encode()
    result=web.parse_html(data,"https://bawaslu.go.id/article")
    assert result["published_at"]=="2026-11-24"
    assert result["title"]=="Officially revised schedule"
    assert "updated official timetable" in result["excerpt"]

def test_live_web_only_search_reads_both_updates_and_keeps_newest_first(monkeypatch):
    cfg=validate(request("What changed in official decisions over the past 2 weeks?"),LEADER)
    calls=[]
    def discover(q,key,model,base,as_of,fresh):
        calls.append(fresh)
        return {"status":"DISCOVERED","queries":["Bahasa Indonesia official","English update"],
            "rows":[{"url":"https://bawaslu.go.id/"+("new" if fresh else "old"),
                     "title":"Newer correction" if fresh else "Older notice","snippet":""}]}
    def read(row):
        when="2026-11-24" if row["url"].endswith("/new") else "2026-11-20"
        return {**source("placeholder",when=when),**row,"read_status":"READ",
                "type":"PUBLIC_OFFICIAL","basis":"LIVE_PUBLIC_LOOKUP"}
    monkeypatch.setattr(web,"discovery",discover)
    monkeypatch.setattr(web,"read_page",read)
    result=web.run(cfg["question"],cfg,"fake-provider-key","model","https://api.openai.com/v1")
    assert calls==[False,True]
    assert result["status"]=="READ_SOURCES_AVAILABLE"
    assert result["sources"][0]["id"]=="WEB-1"
    assert result["sources"][0]["published_at"]=="2026-11-24"
    assert result["sources"][0]["title"]=="Newer correction"
    assert result["read_count"]==2

def test_unverified_demo_record_ids_not_assumed_live_or_verified():
    src=source("SOCIAL-1160","SAVED_SOCIAL","SAVED_SNAPSHOT")
    a=safe_answer(raw(["SOCIAL-1160"]),[src],
                  validate(request("Assess the saved records",sourceMode="SMARTRADAR_ONLY"),LEADER),
                  "NOT_SELECTED")
    assert a["findings"][0]["evidence_class"]=="ATTRIBUTED_SAVED_ALLEGATION_UNVERIFIED"
    assert a["actions_executed"] is False

def test_drafting_followup_has_prior_draft_context_without_automatic_sending():
    cfg=validate(request("Turn that into an email",workflow="DRAFTING",
                         previousDraft="DRAFT MEMO — evidence unverified",
                         history=[{"role":"user","text":"Draft leadership response"}]),LEADER)
    assert cfg["workflow"]=="DRAFTING"
    public={"status":"NOT_SELECTED","sources":[],"queries":[]}
    context=model_context(cfg,jurisdiction(LEADER),public,[])
    assert "evidence unverified" in context["previous_draft_to_edit_not_independent_evidence"]
    answer=safe_answer(raw([]),[],cfg,"NOT_SELECTED")
    assert answer["actions_executed"] is False
    assert answer["staff_review_required"] is True
    assert answer["draft"].startswith("DRAFT MEMO")
