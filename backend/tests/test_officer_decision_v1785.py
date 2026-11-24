"""v178.5 independent Officer Decision AI — no-credit acceptance and privacy guards."""
import inspect
import pytest
from fastapi import HTTPException

from app.officer_action_v3 import contracts,research,claims,legal,quality,decisions,api

GRANT={"role":"National Leadership","status":"Active",
       "permissions":{"view_intelligence":True},
       "geographic_scope":"Nationwide","province":"","regency_city":""}
PUBLIC={"id":"P-1","kind":"OFFICIAL","title":"Official DKPP source",
 "url":"https://dkpp.go.id/berita/official-announcement",
 "published_at":"2026-11-24","updated_at":"",
 "read_status":"READ","excerpt":"BAWASLU officials are mentioned in a published institutional hearing notice. "*6}
SAVED={"id":"R-1","kind":"SAVED_RECORD","title":"Authorized stored observation",
 "url":"","published_at":"2026-11-20","read_status":"SAVED_SNAPSHOT",
 "record_id":"INT-TEST","excerpt":"An officer's unverified summary, not a legal finding"}

def test_clean_new_contract_and_permission():
    v=contracts.validate({"question":"What is new this week?",
                          "source_mode":"WEB_ONLY"},GRANT["role"])
    assert v["recent"] and v["source_mode"]=="WEB_ONLY"
    assert contracts.classification("Draft leadership memo","AUTO")=="DRAFT"
    assert contracts.classification("Explain a legal article","AUTO")=="LEGAL"
    assert not contracts.safe_public_query("Private INT-2044 must not leave platform")
    assert not contracts.safe_public_query("Contact reviewer@example.org")
    with pytest.raises(PermissionError):
        contracts.validate({"question":"Strategy","perspective":"LEADERSHIP"},"Viewer")
    with pytest.raises(ValueError):
        contracts.validate({"question":"x","source_mode":"INVENTED"},"National Leadership")

def test_no_old_assistant_dependency_in_new_engine():
    import pathlib
    root=pathlib.Path(__file__).parents[1]/"app"/"officer_action_v3"
    for path in root.glob("*.py"):
        code=path.read_text(encoding="utf-8")
        assert "from app.ai_assistant_v2" not in code
        assert "from .assistant_" not in code
        assert "from app.assistant_" not in code
        assert "conversationContext" not in code
        assert "previousDraft" not in code
        assert "AssistantThread" not in code

def test_source_read_audit_and_official_scoring():
    assert research.allowed_url("https://www.bawaslu.go.id/news")
    assert not research.allowed_url("http://localhost:8080/admin")
    assert not research.allowed_url("https://evil.com:8443/x")
    assert not research.allowed_url("https://user:password@www.bawaslu.go.id/x")
    assert research.is_official("https://www.dkpp.go.id/berita")
    assert not research.is_official("https://dkpp.go.id.attacker.example/data")
    html=("<html><head><meta property='article:published_time' content='2026-11-24T07:20:00Z'>"
          "<title>Official update</title></head><body><article><p>"+
          "The official record contains an updated session schedule and a dated notice. "*8+
          "</p></article></body></html>").encode()
    p=research.parse_html(html,PUBLIC["url"])
    assert p and p["published_at"]=="2026-11-24"
    assert "updated session schedule" in p["excerpt"]
    assert research.MAX_PAGES<=6

def test_claim_classification_is_evidence_bounded():
    rows=[
        {"claim":"A matter is listed for hearing","status":"PRIMARY_SOURCE_REPORTED","source_ids":["P-1"],"caveat":""},
        {"claim":"A saved record is a confirmed decision","status":"INDEPENDENTLY_CORROBORATED","source_ids":["R-1"],"caveat":""},
        {"claim":"An invented citation","status":"PRIMARY_SOURCE_REPORTED","source_ids":["P-999"],"caveat":""}
    ]
    results=claims.verify_claims(rows,[PUBLIC,SAVED])
    assert results[0]["status"]=="PRIMARY_SOURCE_REPORTED"
    assert results[1]["status"]=="UNRESOLVED"
    assert results[2]["source_ids"]==[]
    assert results[2]["status"]=="UNRESOLVED"
    assert all(r["officer_authenticated"] is False for r in results)

def test_legal_relevance_and_primary_law_require_review():
    l=legal.review_legal([{"issue":"Election supervision",
        "institution":"BAWASLU","legal_reference":"An AI-invented article",
        "applicability":"To be verified","verification_needed":"Read official primary text",
        "source_ids":["R-1"]}],[SAVED])
    assert l[0]["legal_reference"]=="Controlling official provision not verified"
    assert l[0]["officer_review_required"] is True
    assert l[0]["primary_legal_text_confirmed"] is False
    hints=legal.scope_hints("How should DKPP and BAWASLU handle a complaint?")
    assert "ELECTION_ORGANIZER_ETHICS" in hints["signals"]
    assert "DKPP" in hints["authorities"]

def test_quality_filters_unsupported_actions_citations_and_urls():
    raw={"headline":"Hearing","answer":"Reported item [P-1], fabricated [P-999] https://evil.invalid/",
         "key_takeaway":"Source review required","bawaslu_implication":"Check election supervision nexus",
         "recommended_decision":"Preserve original documents","relevance":"DIRECT",
         "claims":[{"claim":"Official notice","status":"PRIMARY_SOURCE_REPORTED","source_ids":["P-1"],
                    "caveat":"Not a verdict"}],
         "legal":[],"options":[],
         "actions":[{"task":"Review source notice","owner_role":"Legal reviewer",
                     "evidence_needed":"Official announcement","deliverable":"Evidence inventory",
                     "decision_gate":"Escalate if BAWASLU nexus proven, otherwise close",
                     "source_ids":["P-1"]},
                    {"task":"Immediately sanction a candidate","owner_role":"Office",
                     "evidence_needed":"News","deliverable":"Fine",
                     "decision_gate":"Immediately","source_ids":["P-1"]}],
         "draft":"","limitations":[]}
    r=quality.finalize(raw,[PUBLIC],"What changed?","RESEARCH","READ","WEB_ONLY",{})
    assert r["relevance"]=="DIRECT"
    assert len(r["actions"])==1
    assert "[P-999]" not in r["answer"]
    assert "https://evil.invalid" not in r["answer"]
    assert not r["quality"]["actions_executed"]
    assert r["quality"]["human_approval_required"]

def test_no_source_is_honest_not_a_legal_or_political_claim():
    r=quality.fallback("Current political scandal?","WEB_ONLY","SEARCH_FAILED",{},[])
    assert r["claims"]==[] and r["legal"]==[] and r["actions"]==[]
    assert r["answer"].startswith("Live public research could not verify")
    assert r["relevance"]=="NOT_ESTABLISHED"

def test_officer_api_web_only_cannot_read_saved_or_old_assistants(monkeypatch):
    calls=[]
    monkeypatch.setattr(api,"profile",lambda *args:GRANT)
    monkeypatch.setattr(api,"has",lambda *args:True)
    monkeypatch.setenv("OPENAI_API_KEY","test-provider-key")
    def web(question,key,model,base,recent=False):
        calls.append("search")
        assert question=="What official notice changed this week?"
        return {"status":"READ","sources":[PUBLIC],
                "queries":["Official notices"],"as_of":"2026-11-24T03:00:00Z"}
    monkeypatch.setattr(api,"public_research",web)
    monkeypatch.setattr(api,"saved_records",lambda *args:
        (_ for _ in ()).throw(AssertionError("WEB_ONLY accessed private records")))
    def ai(q,task,view,records,hints,status,key,model,base):
        calls.append("synthesize")
        assert len(records)==1 and records[0]["id"]=="P-1"
        return {"headline":"Official notice","answer":"A notice was published [P-1].",
                "key_takeaway":"Verify original case documents","bawaslu_implication":"Potential institution scrutiny",
                "recommended_decision":"Start a review","relevance":"DIRECT",
                "claims":[{"claim":"Notice","status":"PRIMARY_SOURCE_REPORTED","source_ids":["P-1"],"caveat":""}],
                "legal":[],"options":[],"actions":[],"draft":"","limitations":[]}
    monkeypatch.setattr(api,"synthesize",ai)
    out=api.analyze({"question":"What official notice changed this week?",
                     "source_mode":"WEB_ONLY"},object(),object())
    assert calls==["search","synthesize"]
    assert out["module"]=="OFFICER_DECISION_AI_INDEPENDENT_V3"
    assert out["research_trail"]["saved_count"]==0
    assert out["report"]["claims"][0]["source_ids"]==["P-1"]
    assert out["audit"]["no_prior_assistant_history_retrieved"]

def test_records_only_does_not_search_external_provider(monkeypatch):
    monkeypatch.setattr(api,"profile",lambda *args:GRANT)
    monkeypatch.setattr(api,"has",lambda *args:True)
    monkeypatch.setenv("OPENAI_API_KEY","")
    monkeypatch.setattr(api,"public_research",lambda *args,**kwargs:
        (_ for _ in ()).throw(AssertionError("Saved-only mode leaked to web")))
    monkeypatch.setattr(api,"saved_records",lambda *args:[SAVED])
    out=api.analyze({"question":"What did our source record say?","source_mode":"RECORDS_ONLY"},
                    object(),object())
    assert out["research_trail"]["web_status"]=="NOT_SELECTED"
    assert out["research_trail"]["saved_count"]==1
    assert out["report"]["quality"]["no_prior_assistant_context"] is True

def test_live_search_missing_key_cannot_invent_recent_updates(monkeypatch):
    monkeypatch.setattr(api,"profile",lambda *args:GRANT)
    monkeypatch.setattr(api,"has",lambda *args:True)
    monkeypatch.delenv("OPENAI_API_KEY",raising=False)
    monkeypatch.setattr(api,"saved_records",lambda *a:
        (_ for _ in ()).throw(AssertionError("Web only cannot use saved")))
    result=api.analyze({"question":"What's the latest official DKPP hearing?","source_mode":"WEB_ONLY"},
                       object(),object())
    assert result["report"]["claims"]==[]
    assert "Live public research" in result["report"]["answer"]
    assert result["research_trail"]["public_read_count"]==0
