"""Provider errors must expose actionable HTTP diagnostics without leaking secrets."""
import httpx
from app.smart_radar_qa_errors import qa_provider_error

def _http_error(status, payload):
    request=httpx.Request("POST","https://api.openai.com/v1/chat/completions")
    response=httpx.Response(status,json=payload,request=request)
    return httpx.HTTPStatusError("provider response",request=request,response=response)

def test_unsupported_parameter_safe():
    err=_http_error(400,{"error":{"type":"invalid_request_error",
        "code":"unsupported_parameter","param":"max_tokens",
        "message":"secret sk-protected-original-post"}})
    result=qa_provider_error(err)
    assert result["provider_status"]==400
    assert "unsupported_parameter" in result["reason"]
    assert "max_tokens" in result["reason"]
    assert "sk-protected" not in result["reason"]
    assert "original-post" not in result["reason"]

def test_quota_failure_safe():
    err=_http_error(429,{"error":{"code":"insufficient_quota","message":"account details"}})
    result=qa_provider_error(err)
    assert "billing" in result["reason"]
    assert "account details" not in result["reason"]

def test_account_auth_failure():
    err=_http_error(401,{"error":{"code":"invalid_api_key"}})
    assert "OPENAI_API_KEY" in qa_provider_error(err)["reason"]

def test_malformed_untrusted_provider_fields_are_not_leaked():
    err=_http_error(400,{"error":{"code":"foo; DELETE ALL","param":"content secret"}})
    result=qa_provider_error(err)
    assert "DELETE" not in result["reason"]
    assert "secret" not in result["reason"]

def test_network_error():
    req=httpx.Request("POST","https://api.openai.com/v1/chat/completions")
    assert "contact" in qa_provider_error(httpx.ConnectError("oops",request=req))["reason"]
