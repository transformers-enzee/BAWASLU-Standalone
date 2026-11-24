"""AI-4 independent API. Does not mount, retire, or modify another assistant.

Existing auth, access grants and authorised query selectors are shared.
AI-4's prompt and conversations are not migrated from historical assistants.
"""
import os
import re
import uuid
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.auth import current_user
from app.models import User
from app.access import profile,has
from app.db import get_db
from app.unified_ai.web import run as search_public_web
from app.unified_ai.saved import collect as authorised_records
from . import attachments
from .core import validate,source_preferences,profile_context,synthesis,sanitize

router=APIRouter(prefix="/api/ai-4",tags=["AI-4 evaluation"])
FOLLOWUP=re.compile(r"\b(shorten|rewrite|revise|turn into|draft|memo|email|summarise|summarize|"
                    r"strategy|tactics|action plan|ringkas|perbaiki|ubah|buatkan|surat|"
                    r"strategi|rencana|tindak lanjut)\b",re.I)


class LinkInput(BaseModel):
    conversation_id:str
    url:str


def grant_for(db,user):
    grant=profile(db,user)
    if not has(grant,"view_intelligence"):
        raise HTTPException(403,"Active permission to view intelligence is required")
    return grant


@router.post("/upload")
async def upload(conversation_id:str=Form(...),file:UploadFile=File(...),
                 user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    raw=await file.read(attachments.MAX_BYTES+1)
    return {"attachment":attachments.add_file(user.id,conversation_id,grant,
                           file.filename or "",raw)}


@router.post("/link")
def link(body:LinkInput,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return {"attachment":attachments.add_link(user.id,body.conversation_id,grant,body.url)}


@router.get("/attachments/{conversation_id}")
def list_attachments(conversation_id:str,user:User=Depends(current_user),
                     db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return {"attachments":attachments.list_items(user.id,conversation_id,grant),
            "retention":"PER_PROCESS_EPHEMERAL_UP_TO_12_HOURS"}


@router.delete("/attachments/{conversation_id}/{attachment_id}")
def remove_attachment(conversation_id:str,attachment_id:str,
                      user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return attachments.remove(user.id,conversation_id,grant,attachment_id)


@router.delete("/conversation/{conversation_id}")
def clear_conversation(conversation_id:str,user:User=Depends(current_user),
                       db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return attachments.clear(user.id,conversation_id,grant)


@router.post("/chat")
def chat(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    cfg=validate(body,grant)
    conversation_id=body.get("conversationId")
    state=attachments.bind_mode(user.id,conversation_id,grant,cfg["source_mode"])
    saved=[];warnings=[]
    key=os.getenv("OPENAI_API_KEY","").strip()
    model=(os.getenv("OPENAI_AI4_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    base=(os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip()
    prefs=source_preferences(cfg["source_mode"])
    # Strict Web-only boundary: does not import or invoke any saved-record
    # collector, even if public search fails or the question is a draft.
    public={"status":"NOT_SELECTED","sources":[],"as_of":None,"queries":[],"attempts":[]}
    if prefs["publicWeb"]:
        # Ordinary follow-up drafting may reuse sources independently read in
        # this AI-4 session. They are labelled as prior snapshots, NOT live
        # searches. Current-period questions always perform fresh discovery.
        prior=state.get("last_public") or {}
        is_followup=bool(FOLLOWUP.search(cfg["question"]) and not cfg["recent"] and prior.get("sources"))
        if is_followup:
            public={"status":"CARRIED_FORWARD_READ_SNAPSHOT",
                    "sources":[dict(s) for s in prior["sources"]],
                    "as_of":prior.get("as_of"),
                    "queries":prior.get("queries",[]),
                    "attempts":[{"phase":"follow-up","status":"PREVIOUSLY_READ","discovered":len(prior["sources"])}]}
        else:
            public=search_public_web(cfg["question"],{"sources":{"publicWeb":True},
                "recent":cfg["recent"],"as_of":cfg["today"],"window":cfg.get("window")},key,model,base)
            if public["status"]=="READ_SOURCES_AVAILABLE":
                state["last_public"]={"sources":[dict(s) for s in public["sources"]],
                                      "as_of":public.get("as_of"),
                                      "queries":public.get("queries",[])}
    if prefs["smartRadar"]:
        saved,warnings=authorised_records(db,grant,cfg["question"],prefs,cfg.get("window"))
    uploaded=attachments.evidence(user.id,conversation_id,grant)
    if prefs["publicWeb"] and public["status"] not in ("READ_SOURCES_AVAILABLE","CARRIED_FORWARD_READ_SNAPSHOT"):
        warnings.insert(0,"Live public search did not provide readable sources ("+public["status"]+
                        "). SmartRadar records were not substituted; ask to change source mode.")
    if public["status"]=="CARRIED_FORWARD_READ_SNAPSHOT":
        warnings.append("Public links are retained from the prior conversation turn, not freshly rechecked.")
    source_rows=[*public.get("sources",[]),*saved,*uploaded]
    generated,status=synthesis(cfg,profile_context(grant),public,saved,uploaded,key,model,base)
    response=sanitize(generated,source_rows,cfg,public["status"])
    if status!="COMPLETE":
        warnings.append("AI-4 response generation is unavailable ("+status+"); no fictional sourced answer was substituted.")
    # Do not persist generated case conclusions or conversations to any shared
    # assistant_history or SmartRadar model. Only processed attachments and
    # previously read public sources are ephemeral to this authenticated session.
    display=[]
    for row in source_rows[:40]:
        display.append({k:row.get(k) for k in (
            "id","type","title","url","resolved_url","basis","read_status","published_at",
            "updated_at","location_verified","location","section","duplicate_of","within_period",
            "reliability","reason","review_status")})
    return {"assistant":"AI-4","turn_id":uuid.uuid4().hex,"workspace":cfg["workspace"],"perspective":cfg["perspective"],
        "source_mode":cfg["source_mode"],"answer":response,
        "source_trail":{"sources":display,
            "public_status":public["status"],
            "searched_at":public.get("as_of"),"queries":public.get("queries",[]),
            "passes":public.get("attempts",[]),
            "read_public_count":sum(x.get("read_status")=="READ" for x in public.get("sources",[])),
            "saved_count":len(saved),"attached_count":len(uploaded),
            "period":cfg.get("window"),"warnings":warnings,
            "attachment_retention":"PER_PROCESS_EPHEMERAL_UP_TO_12_HOURS"},
        "synthesis_status":status,"created_at":datetime.now(timezone.utc).isoformat(),
        "human_review_required":True,
        "actions_executed":False}


@router.post("/feedback")
def feedback(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    cid=body.get("conversation_id")
    state=attachments.session(user.id,cid,grant,False)
    if state is None:raise HTTPException(404,"AI-4 conversation expired")
    turn_id=body.get("turn_id")
    if not isinstance(turn_id,str) or not re.fullmatch(r"[a-f0-9]{32}",turn_id):
        raise HTTPException(422,"Invalid answer reference")
    for key in ("clarity","source_quality","usefulness"):
        if type(body.get(key)) is not int or not 1<=body[key]<=5:
            raise HTTPException(422,"Evaluation scores must be integers from 1 through 5")
    note=body.get("note") or ""
    if not isinstance(note,str) or len(note)>400:
        raise HTTPException(422,"Evaluation note must be at most 400 characters")
    rows=state.setdefault("feedback",[])
    if len(rows)>=30:raise HTTPException(422,"Evaluation limit reached for this conversation")
    rows.append({"turn_id":turn_id,"clarity":body["clarity"],
                 "source_quality":body["source_quality"],"usefulness":body["usefulness"],
                 "note":note,"created_at":datetime.now(timezone.utc).isoformat()})
    return {"saved":True,"count":len(rows),"retention":"EPHEMERAL_12_HOURS"}


@router.get("/feedback/{conversation_id}")
def list_feedback(conversation_id:str,user:User=Depends(current_user),
                  db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    state=attachments.session(user.id,conversation_id,grant,False)
    return {"feedback":list(state.get("feedback",[])) if state else [],
            "retention":"EPHEMERAL_12_HOURS"}
