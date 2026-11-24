"""Safe, deterministic web-search error diagnostics for BOTH assistant endpoints.

No real network calls, provider credits, data writes, or private source exports.
"""
import httpx
from app.assistant_orchestration import research_public_web

class FakeResponse:
    def __init__(self,status_code=200,payload=None):
        self.status_code=status_code
        self.payload=payload or {}
    def json(self):return self.payload

class FakeClient:
    response=FakeResponse()
    last_request=None
    def __init__(self,**kwargs):pass
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def post(self,url,headers,json):
        FakeClient.last_request={"url":url,"json":json}
        return self.response

def call(diag):
    return research_public_web("Latest public BAWASLU news","fake-key",
        "standard-model","https://api.openai.com/v1", diagnostics=diag)

def test_provider_http_failure_is_identifiable_without_promoting_to_citation(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    monkeypatch.setattr(httpx,"Client",FakeClient)
    FakeClient.response=FakeResponse(403)
    diag={}
    assert call(diag) is None
    assert diag=={"status":"PROVIDER_HTTP_403","source_count":0}
    assert FakeClient.last_request["json"]["tools"]==[{"type":"web_search"}]
    assert FakeClient.last_request["json"]["max_output_tokens"]==2400

def test_incomplete_response_provides_reason_code(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    monkeypatch.setattr(httpx,"Client",FakeClient)
    FakeClient.response=FakeResponse(payload={"status":"incomplete",
        "incomplete_details":{"reason":"max_output_tokens"}})
    diag={}
    assert call(diag) is None
    assert diag["status"]=="PROVIDER_INCOMPLETE_max_output_tokens"

def test_tool_not_executed_is_not_public_research(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    monkeypatch.setattr(httpx,"Client",FakeClient)
    FakeClient.response=FakeResponse(payload={"status":"completed","output":[
        {"type":"message","content":[{"type":"output_text","text":"Uncited text"}]}]})
    diag={}
    assert call(diag) is None
    assert diag["status"]=="PROVIDER_SEARCH_TOOL_NOT_EXECUTED"

def test_distinct_configuration_errors(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","false")
    diag={}
    assert call(diag) is None
    assert diag["status"]=="SEARCH_DISABLED_BY_CONFIGURATION"
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    diag={}
    assert research_public_web("Latest public news","","model",
        "https://api.openai.com/v1",diagnostics=diag) is None
    assert diag["status"]=="PROVIDER_KEY_UNAVAILABLE"

def test_web_model_is_overridable_without_changing_general_ai(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSISTANT_WEB_SEARCH","true")
    monkeypatch.setenv("OPENAI_WEB_SEARCH_MODEL","web-capable-model")
    monkeypatch.setattr(httpx,"Client",FakeClient)
    FakeClient.response=FakeResponse(400)
    diag={}
    assert call(diag) is None
    assert FakeClient.last_request["json"]["model"]=="web-capable-model"
    assert diag["status"]=="PROVIDER_HTTP_400"
