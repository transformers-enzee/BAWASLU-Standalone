"""Live-web integration acceptance without network/API credits.

These checks exercise the real POST chat handler in Web only mode while mocking
only external provider and page HTTP results; they must not be presented as a
live paid-provider test.
"""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException

from app import assistant_live_web as live
from app import ai_assistant_v2 as v2

GRANT={"status":"Active","role":"National Leadership",
       "permissions":{"view_intelligence":True}}
OLD="https://www.mpr.go.id/berita/older"
NEW="https://www.mpr.go.id/berita/updated"


def _page(url,when,title):
    return {"url":url,"status":"READ","reason":"Page opened",
        "title":title,"published_at":when,"updated_at":"",
        "excerpt":"Official record describing the scheduled event, including changes and its source context. "*8}

def _provider_summary():
    return {"summary":"Search provider overview (not source proof)",
            "urls":[OLD,NEW],"sources":[{"url":OLD},{"url":NEW}],
            "retrieved_at":"2026-11-24T01:01:00Z","search_queries":["perubahan jadwal terbaru","latest postponed hearing"],
            "freshness_check_requested":True}


def test_three_source_modes_are_strict_server_side():
    src=live.source_mode_sources("WEB_ONLY")
    assert src=={"smartRadar":False,"publicWeb":True,"legalReferences":False,"attachments":False}
    assert live.source_mode_sources("SMARTRADAR_ONLY")["publicWeb"] is False
    assert live.source_mode_sources("WEB_SMARTRADAR")["smartRadar"]
    assert v2.validate({"question":"What is the latest official date?",
        "sourceMode":"WEB_ONLY","sources":{"smartRadar":True,"publicWeb":True,"legalReferences":True}},GRANT)["sources"]=={
            "smartRadar":False,"publicWeb":True,"legalReferences":False}
    with pytest.raises(HTTPException):
        v2.validate({"question":"Explain the news","sourceMode":"WEB_NOT_VALID"},GRANT)


def test_recent_bilingual_and_update_queries():
    plan=live.search_plan("What changed this week in the BAWASLU hearing?","2026-11-24")
    assert len(plan["queries"])==2
    assert "Indonesia" in plan["queries"][0]
    assert "latest" in plan["queries"][1]
    assert "postponed" in plan["freshness_query"]
    assert live.recent_research("Tren 2 minggu terakhir")
    assert not live.recent_research("Explain duties of BAWASLU")


def test_read_pages_sorted_by_actual_publication_date_not_snippet_order():
    rows=[_page(OLD,"2026-11-20","Older notice"),_page(NEW,"2026-11-24","Updated schedule")]
    def fake_fetch(r):return next(x for x in rows if x["url"]==r["url"])
    result=live.verify_public_pages(_provider_summary(),fetcher=fake_fetch)
    assert result["urls"]==[NEW,OLD]    # Latest readable notice is model context first
    assert result["summary"].index("Updated schedule") < result["summary"].index("Older notice")
    assert result["read_count"]==2


def test_snippet_and_inaccessible_never_count_as_read():
    def fake_fetch(row):return {**row,"status":"SNIPPET_ONLY","reason":"Blocked page",
                                "excerpt":"Provider snippet, not the opened page"}
    result=live.verify_public_pages(_provider_summary(),fetcher=fake_fetch)
    assert result["read_count"]==0 and result["urls"]==[]
    assert result["search_status"]=="NO_READABLE_PUBLIC_PAGES"


def test_html_parser_reads_article_and_dates():
    html=('''<html><head><meta property="article:published_time" content="2026-11-24T09:00:00+07:00">
    <title>Old headline</title></head><body><article><h1>Official corrected date</h1><p>'''
        +'The official announcement explains the election event and the revised meeting schedule. '*6+
        '''</p></article></body></html>''')
    d=live.parse_public_html(html,NEW)
    assert d["published_at"]=="2026-11-24"
    assert "revised meeting schedule" in d["excerpt"]
    assert d["title"]=="Official corrected date"


def test_web_only_current_question_runs_fresh_search_before_any_private_read(monkeypatch):
    calls=[]
    monkeypatch.setattr(v2,"profile",lambda *a:GRANT)
    monkeypatch.setattr(v2,"has",lambda *a:True)
    monkeypatch.setattr(v2,"gather",lambda *a:(_ for _ in ()).throw(AssertionError("private retrieval forbidden")))
    monkeypatch.setenv("OPENAI_API_KEY","synthetic-test-key")
    import app.assistant_orchestration as orch
    def web_search(question,*args,**kwargs):
        calls.append("web_search")
        assert "Gibran" in question
        return _provider_summary()
    monkeypatch.setattr(orch,"research_public_web",web_search)
    def open_pages(payload):
        calls.append("page_read")
        return live.verify_public_pages(payload,fetcher=lambda row:_page(row["url"],
            "2026-11-24" if row["url"]==NEW else "2026-11-20",
            "Updated notice" if row["url"]==NEW else "Old notice"))
    monkeypatch.setattr(v2,"verify_public_pages",open_pages)
    def model(context,key):
        calls.append("model")
        assert not any(x["type"]!="PUBLIC_WEB" for x in context["source_records"])
        assert context["source_records"][0]["url"]==NEW
        assert context["source_records"][0]["read_status"]=="READ"
        assert context["history_for_revisions_not_evidence"]==[]
        assert context["previous_draft_for_editing_not_evidence"]==""
        assert context["public_research"].index("Updated notice")<context["public_research"].index("Old notice")
        return {"summary":"The updated official date supersedes the earlier notice [WEB-1]. "
                "BAWASLU should check the institutional implications.",
                "findings":[{"claim":"The updated notice is newer [WEB-1]","source_ids":["WEB-1"],
                             "uncertainty":"Verify current official status"}],
                "options":[],"plan":[],"draft":"","uncertainties":[]}
    monkeypatch.setattr(v2,"_model_answer",model)
    reply=v2.chat({"question":"What is the current latest Gibran hearing schedule?",
         "sourceMode":"WEB_ONLY","sources":{"smartRadar":True,"publicWeb":True,"legalReferences":True}},
         object(),object())
    assert calls==["web_search","page_read","model"]
    assert reply["source_mode"]=="WEB_ONLY"
    assert reply["answer"]["findings"][0]["source_ids"]==["WEB-1"]
    assert reply["sources"][0]["url"]==NEW
    assert reply["sources"][0]["read_status"]=="READ"
    assert reply["web_pages"][0]["published_at"]=="2026-11-20"
    assert reply["web_search_status"]=="READ_SOURCES_AVAILABLE"
    assert not any(r["type"]=="FORMAL_INTELLIGENCE" for r in reply["sources"])


def test_failed_live_web_disclosed_before_saved_record_answer(monkeypatch):
    monkeypatch.setattr(v2,"profile",lambda *a:GRANT)
    monkeypatch.setattr(v2,"has",lambda *a:True)
    monkeypatch.setenv("OPENAI_API_KEY","test-key")
    import app.assistant_orchestration as orch
    monkeypatch.setattr(orch,"research_public_web",lambda *a,**k:None)
    monkeypatch.setattr(v2,"gather",lambda *a:([{
        "id":"INT-1","type":"FORMAL_INTELLIGENCE","title":"Saved record","excerpt":"Unverified snapshot",
        "url":"","date":"","location":"","location_verified":False}],[]))
    monkeypatch.setattr(v2,"_model_answer",lambda *a:{"summary":"Saved observation only.",
        "findings":[],"options":[],"plan":[],"draft":"","uncertainties":[]})
    reply=v2.chat({"question":"What changed this week?","sourceMode":"WEB_SMARTRADAR"},object(),object())
    assert reply["answer"]["summary"].startswith("Live public-web verification unavailable:")
    assert len([s for s in reply["sources"] if s["type"]=="PUBLIC_WEB"])==0


def test_saved_only_does_not_call_search(monkeypatch):
    monkeypatch.setattr(v2,"profile",lambda *a:GRANT)
    monkeypatch.setattr(v2,"has",lambda *a:True)
    monkeypatch.setenv("OPENAI_API_KEY","")
    monkeypatch.setattr(v2,"gather",lambda *a:([],[]))
    import app.assistant_orchestration as orch
    monkeypatch.setattr(orch,"research_public_web",
        lambda *a,**k:(_ for _ in ()).throw(AssertionError("No search permitted")))
    reply=v2.chat({"question":"What is in saved records?","sourceMode":"SMARTRADAR_ONLY"},object(),object())
    assert reply["web_search_status"]=="WEB_NOT_SELECTED"
    assert reply["web_pages"]==[]


def test_no_actual_read_means_no_web_citations(monkeypatch):
    monkeypatch.setattr(v2,"profile",lambda *a:GRANT)
    monkeypatch.setattr(v2,"has",lambda *a:True)
    monkeypatch.setenv("OPENAI_API_KEY","test-key")
    import app.assistant_orchestration as orch
    monkeypatch.setattr(orch,"research_public_web",lambda *a,**k:_provider_summary())
    monkeypatch.setattr(v2,"verify_public_pages",lambda r:live.verify_public_pages(
        r,fetcher=lambda row:{**row,"status":"INACCESSIBLE","reason":"Blocked"}))
    monkeypatch.setattr(v2,"_model_answer",lambda *a:{"summary":"No verified findings",
        "findings":[],"options":[],"plan":[],"draft":"","uncertainties":[]})
    reply=v2.chat({"question":"Latest official hearing this week","sourceMode":"WEB_ONLY"},object(),object())
    assert reply["web_search_status"]=="NO_READABLE_PUBLIC_PAGES"
    assert not any(r["type"]=="PUBLIC_WEB" for r in reply["sources"])
    assert reply["answer"]["summary"].startswith("Live public-web verification unavailable:")


def test_reader_opens_html_only_after_safe_peer_verification(monkeypatch):
    from app import assistant_live_web as module
    monkeypatch.setattr(module,"_safe_page_url",lambda url:True)
    class Peer:
        def get_extra_info(self,name):
            assert name=="server_addr"
            return ("8.8.8.8",443)
    class Response:
        status_code=200
        headers={"content-type":"text/html; charset=utf-8"}
        extensions={"network_stream":Peer()}
        encoding="utf-8"
        def __enter__(self):return self
        def __exit__(self,*args):return None
        def iter_bytes(self,chunk_size=8192):
            text=("<html><head><meta property='article:published_time' content='2026-11-24'>"
                  "<title>Corrected schedule</title></head><body><article><p>"
                  +("An official meeting notice has been published with a revised session date. "*7)+
                  "</p></article></body></html>")
            yield text.encode("utf-8")
    class Client:
        def stream(self,verb,url,**kwargs):
            assert verb=="GET" and kwargs["follow_redirects"] is False
            return Response()
    row={"url":NEW,"title":"Search title","snippet":""}
    result=module._read_one(row,Client())
    assert result["status"]=="READ"
    assert result["published_at"]=="2026-11-24"
    assert "revised session date" in result["excerpt"]


def test_reader_rejects_private_peer_even_after_public_dns_check(monkeypatch):
    from app import assistant_live_web as module
    monkeypatch.setattr(module,"_safe_page_url",lambda url:True)
    class Peer:
        def get_extra_info(self,name):return ("127.0.0.1",443)
    class Response:
        status_code=200
        headers={"content-type":"text/html"}
        extensions={"network_stream":Peer()}
        def __enter__(self):return self
        def __exit__(self,*args):return None
    class Client:
        def stream(self,*a,**kw):return Response()
    result=module._read_one({"url":NEW,"snippet":""},Client())
    assert result["status"]=="INACCESSIBLE"
    assert "peer address" in result["reason"]


def test_legacy_web_only_server_routing_overrides_all_private_flags():
    from app.assistant_workflows import normalize_workflow_request
    choice=normalize_workflow_request({"question":"Latest election news?",
        "sourceMode":"WEB_ONLY",
        "sourceSelection":{"smartRadar":True,"publicWeb":True,
                           "legalReferences":True,"attachments":True}})
    assert choice["source_mode"]=="WEB_ONLY"
    assert choice["sources"]=={"smartRadar":False,"publicWeb":True,
                               "legalReferences":False,"attachments":False}
