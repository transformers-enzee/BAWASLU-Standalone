"""The only active /api/ai-assistant endpoint. Fresh implementation.

Web-only never opens saved source collectors. Mixed mode attributes independently
read public pages separately from permission-scoped fixed observations.
"""
import os
import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.access import has, profile
from app.auth import current_user
from app.db import get_db
from app.models import User
from .contract import validate, jurisdiction, REFERENCE
from .web import run as public_research
from .saved import collect as saved_research
from .answer import request_ai, safe_answer, model_context

router=APIRouter(prefix="/api/ai-assistant",tags=["smart-radar-unified-assistant"])
LOG=logging.getLogger(__name__)


def source_consultation(config,public,saved):
    selected=config["sources"]
    public_rows=public.get("sources",[])
    rows=[
      {"key":"publicWeb","label":"Public web, official sources and indexed social",
       "selected":selected["publicWeb"],"status":public.get("status") if selected["publicWeb"] else "NOT_SELECTED",
       "read_count":sum(s["read_status"]=="READ" for s in public_rows),
       "snippet_count":sum(s["read_status"]=="SNIPPET_ONLY" for s in public_rows),
       "inaccessible_count":sum(s["read_status"]=="INACCESSIBLE" for s in public_rows),
       "basis":"LIVE_PUBLIC_LOOKUP" if selected["publicWeb"] else "NOT_SELECTED"},
      {"key":"smartRadar","label":"Authorised saved SmartRadar intelligence",
       "selected":selected["smartRadar"],
       "status":"CONSULTED" if any(s["type"]!="SAVED_LEGAL" for s in saved) else
                "SELECTED_NO_MATCH" if selected["smartRadar"] else "NOT_SELECTED",
       "count":sum(s["type"]!="SAVED_LEGAL" for s in saved),
       "basis":"FIXED_SAVED_SNAPSHOT" if selected["smartRadar"] else "NOT_SELECTED"},
      {"key":"legalReferences","label":"Authorized saved legal reference library",
       "selected":selected["legalReferences"],
       "status":"CONSULTED" if any(s["type"]=="SAVED_LEGAL" for s in saved) else
                "SELECTED_NO_MATCH" if selected["legalReferences"] else "NOT_SELECTED",
       "count":sum(s["type"]=="SAVED_LEGAL" for s in saved),
       "basis":"FIXED_SAVED_SNAPSHOT" if selected["legalReferences"] else "NOT_SELECTED"}
    ]
    return rows


def revision_topic(cfg):
    """A short edit request may reuse prior USER topic, never old AI prose."""
    q=cfg["question"]
    if cfg["workflow"]!="DRAFTING" or not cfg["previous_draft"] or len(q.split())>=12:
        return q
    users=[r["text"] for r in cfg["history"] if r["role"]=="user"]
    return next((topic for topic in reversed(users)
                 if len(topic.split())>=5 and not REFERENCE.search(topic)),q)


def api_result(config,grant,public,saved,answer,synthesis_status,warnings):
    sources=[*public.get("sources",[]),*saved]
    display=[]
    for s in sources:
        row={k:s.get(k) for k in ("id","type","title","url","resolved_url","read_status",
              "basis","reliability","reason","published_at","updated_at","location",
              "location_verified","duplicate_of","review_status","within_period","document_type")}
        # Permission-filtered excerpts are shown only to the authenticated staff,
        # as original evidence, not a public source or third-party transmission.
        row["excerpt"]=str(s.get("excerpt") or "")[:1200] if s.get("read_status") in ("READ","SAVED_SNAPSHOT") else ""
        display.append(row)
    return {"assistant_version":"UNIFIED_AI_V1","workspace":config["workspace"],
        "perspective":config["perspective"],"workflow":config["workflow"],
        "source_mode":config["source_mode"],
        "source_consultation":source_consultation(config,public,saved),
        "sources":display,"answer":answer,
        "public_research":{"status":public["status"],
            "queries":public.get("queries",[])[:20],
            "attempts":public.get("attempts",[])[:4],
            "as_of":public.get("as_of"),
            "read_count":sum(s["read_status"]=="READ" for s in public.get("sources",[])),
            "date_window":config.get("window")},
        "warnings":warnings,"synthesis_status":synthesis_status,
        "review_policy":"DRAFT_ONLY_AUTHORISED_OFFICER_REVIEW",
        "officer_scope":jurisdiction(grant),
        "as_of":datetime.now(timezone.utc).isoformat()}


@router.post("/chat")
def chat(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=profile(db,user)
    if not has(grant,"view_intelligence"):
        raise HTTPException(403,"An active intelligence-view permission is required")
    cfg=validate(body,grant)
    key=os.getenv("OPENAI_API_KEY","").strip()
    base=(os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip().rstrip("/")
    model=(os.getenv("OPENAI_UNIFIED_ASSISTANT_MODEL") or os.getenv("OPENAI_MODEL") or
           "gpt-6-luna").strip()
    question=revision_topic(cfg)
    # Crucial: Web-only never calls the saved-source collector. Not even a
    # hidden SmartRadar search for recommendations, revisions or fallback.
    public=public_research(question,cfg,key,model,base)
    saved=[];warnings=[]
    if cfg["sources"]["smartRadar"] or cfg["sources"]["legalReferences"]:
        saved,warnings=saved_research(db,grant,cfg["question"],cfg["sources"],cfg.get("window"))
    if cfg["sources"]["publicWeb"] and public["status"]!="READ_SOURCES_AVAILABLE":
        warnings.insert(0,"Live public research did not return readable primary pages ("+
                        public["status"]+"). Do not treat saved records or AI general knowledge as current verification.")
    if cfg.get("window"):
        warnings.append("Recent-period comparisons require a complete and comparable source population; "
                        "selected reports alone do not establish national social trends.")
    # The model never receives old private source observations when the active
    # source mode is WEB_ONLY. Old assistant prose cannot become proof.
    if cfg["source_mode"]=="WEB_ONLY":
        cfg["history"]=[r for r in cfg["history"] if r["role"]=="user"][-4:]
    context=model_context(cfg,jurisdiction(grant),public,saved)
    raw=None;status="PROVIDER_NOT_CONFIGURED"
    if key:
        raw,status=request_ai(cfg,context,key,model,base)
        if status!="COMPLETE":
            LOG.warning("UNIFIED_AI_SYNTHESIS_STATUS=%s",status)
            warnings.append("AI synthesis unavailable ("+status+"); no unverified factual answer was substituted.")
    else:
        warnings.append("AI synthesis provider is not configured.")
    answer=safe_answer(raw,public.get("sources",[])+saved,cfg,public["status"])
    # Never generate a deceptively complete sourced draft without eligible
    # evidence. General conceptual guidance remains clearly provisional.
    return api_result(cfg,grant,public,saved,answer,status,warnings)
