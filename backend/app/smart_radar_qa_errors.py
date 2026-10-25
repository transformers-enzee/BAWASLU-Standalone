"""Redacted, actionable provider diagnostics for QA-only model requests.

Never return provider response bodies, credentials, prompts, or original posts.
"""
import re
import httpx

def _safe_name(value):
    if not isinstance(value,str):
        return None
    return value[:64] if re.fullmatch(r"[a-zA-Z0-9_.-]{1,64}",value) else None

def qa_provider_error(exc):
    if isinstance(exc,httpx.HTTPStatusError):
        status=exc.response.status_code
        detail={}
        try:
            data=exc.response.json()
            if isinstance(data,dict) and isinstance(data.get("error"),dict):
                detail=data["error"]
        except (ValueError,TypeError):
            pass
        code=_safe_name(detail.get("code"))
        param=_safe_name(detail.get("param"))
        kind=_safe_name(detail.get("type"))
        if status==400:
            message="AI request rejected: check model compatibility and request parameters"
        elif status==401:
            message="AI authentication failed: check the existing OPENAI_API_KEY in Render"
        elif status==403:
            message="AI access denied: the API key or project may lack permission for this model"
        elif status==404:
            message="AI model/endpoint unavailable: check the existing OPENAI_MODEL setting"
        elif status==429 and code=="insufficient_quota":
            message="OpenAI API quota/billing exhausted: check account/project billing"
        elif status==429:
            message="OpenAI API rate limit or quota reached: check usage limits"
        elif status>=500:
            message="AI provider temporary server error"
        else:
            message="AI provider rejected the request"
        suffix=", ".join(x for x in [code,kind,param] if x)
        return {"reason":f"OpenAI HTTP {status}: {message}"+(f" [{suffix}]" if suffix else ""),
                "provider_status":status,"provider_code":code,"provider_param":param}
    if isinstance(exc,httpx.TimeoutException):
        return {"reason":"AI provider request timed out; no QA result saved"}
    if isinstance(exc,httpx.RequestError):
        return {"reason":"Unable to contact the AI provider; check network and OPENAI_BASE_URL"}
    if isinstance(exc,(ValueError,KeyError,IndexError,TypeError)):
        return {"reason":"AI returned an unusable category/JSON/evidence quote; no QA result saved"}
    return {"reason":"QA assessment failed without a saved result"}
