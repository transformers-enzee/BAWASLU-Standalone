"""Standalone Officer Decision AI v3 API; not an extension of either prior assistant."""
import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.access import has, profile
from app.auth import current_user
from app.db import get_db
from app.models import User
from .contracts import classification,validate,utc_now
from .depth import depth_for,objectives
from .research import public_research,saved_records
from .legal import scope_hints
from .decisions import synthesize
from .quality import finalize

router=APIRouter(prefix="/api/officer-decision-ai",tags=["officer-decision-ai-independent"])
LOG=logging.getLogger(__name__)

def _eligible_sources(records):
    return [r for r in records if r.get("read_status") in ("READ","SAVED_SNAPSHOT")]

@router.post("/analyze")
def analyze(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=profile(db,user)
    if not has(grant,"view_intelligence"):
        raise HTTPException(status_code=403,detail="Active intelligence access required")
    try:
        cfg=validate(body,grant.get("role",""))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc))
    question=cfg["question"]
    mode=cfg["source_mode"]
    task=classification(question,cfg["task"])
    key=os.getenv("OPENAI_API_KEY","").strip()
    base=(os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    model=(os.getenv("OPENAI_OFFICER_DECISION_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-6-luna").strip()
    # Fresh search precedes any optional saved-source lookup. The only data
    # sent to the search provider is the user's privacy-filtered question.
    public={"status":"NOT_SELECTED","sources":[],"queries":[],"as_of":utc_now()}
    if mode!="RECORDS_ONLY":
        public=public_research(question,key,model,base,recent=cfg["recent"])
    internal=[]
    if mode!="WEB_ONLY":
        try:
            internal=saved_records(db,grant,question)
        except Exception:
            db.rollback()
            LOG.exception("OFFICER_DECISION_V3_AUTHORIZED_RECORDS_FAILED")
            internal=[]
    sources=public["sources"]+internal
    hints=scope_hints(question)
    result=synthesize(question,task,cfg["perspective"],_eligible_sources(sources),
                      hints,public["status"],key,model,base)
    report=finalize(result,sources,question,task,public["status"],mode,hints)
    if result is None and _eligible_sources(sources):
        report["limitations"].insert(0,"Research sources were retrieved, but answer synthesis did not complete. No complete analytical report was generated.")
    # Never expose raw page text, sensitive record excerpts or credentials
    # through Research Trail. Only selected structured claims are presented.
    trail=[]
    for src in sources:
        trail.append({k:src.get(k,"") for k in
                      ("id","kind","record_id","title","url","published_at",
                       "updated_at","read_status","reason","review_status","resolved_url",
                       "document_type","units_inspected","extraction_notes","objective")})
    return {"module":"OFFICER_DECISION_AI_INDEPENDENT_V3",
            "version":"2.0","scope":"CURRENT_AUTHORIZED_USER_NO_SHARED_ASSISTANT_CONTEXT",
            "task":task,"source_mode":mode,"perspective":cfg["perspective"],
            "research_depth":depth_for(question),"requested_dimensions":[name for name,_ in objectives(question)],
            "synthesis_status":"GENERATED" if result else "UNAVAILABLE",
            "report":report,"research_trail":{
                "retrieved_at":public.get("as_of"),"web_status":public["status"],
                "search_queries":public.get("queries",[])[:24],
                "search_passes":public.get("search_passes",[]),
                "sources":trail,"public_read_count":sum(s.get("read_status")=="READ" for s in sources),
                "saved_count":len(internal),"search_is_live":any(p.get("status") in ("DISCOVERED","NO_ATTRIBUTABLE_URLS") for p in public.get("search_passes",[]))},
            "audit":{"read_only":True,"no_case_created":True,"no_assignment_created":True,
                     "no_prior_assistant_history_retrieved":True,"human_review_required":True}}
