"""AI-5 independent API: general research ⇄ BAWASLU action, source controls,
permission-scoped attachments, retained context and real authenticated exports.
"""
import io
import os
import re
import secrets
import logging
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,File,Form,UploadFile,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import current_user
from app.access import profile,has
from app.models import User
from app.ai4 import attachments as parsers
from app.unified_ai.saved import collect as saved_research
from app.ai4.core import profile_context
from . import state,web,engine,export

router=APIRouter(prefix="/api/ai-5",tags=["AI-5 general research"])
LOG=logging.getLogger(__name__)

REWRITE=re.compile(
 r"^\s*(?:please\s+)?(?:shorten|rewrite|revise|reformat|rephrase|"
 r"edit|translate|turn (?:this|that|it|the above|the earlier|the latest)|"
 r"make (?:this|that|it) (?:a|an)|"
 r"summarize (?:this|that|it|the above)|summarise (?:this|that|it|the above)|"
 r"ringkas(?:lah|kan)?|persingkat|perbaiki|ubah(?:lah)?|"
 r"terjemahkan|jadikan|buat (?:ini|itu) menjadi|"
 r"export|convert to|put (?:this|it) into)\b",re.I)
APPLY=re.compile(r"^\s*(?:use (?:this|it|the findings) for bawaslu|"
                 r"how (?:does|can|would) (?:this|it) apply to (?:my|our) office|"
                 r"apply (?:this|it) to (?:my|our) office|"
                 r"bagaimana (?:hasil ini|ini|itu) (?:untuk|diterapkan)|"
                 r"terapkan (?:ini|hasil ini))\b",re.I)
ATTACHMENT_ONLY=re.compile(r"(?:the uploaded|attached (?:document|file)|this file|"
                            r"the PDF|this PDF|file terlampir|dokumen terlampir|berkas ini)",re.I)
NEW_EXTERNAL=re.compile(r"\b(latest|current|recent|verify online|search the web|"
                        r"check official|terbaru|terkini|cek online|"
                        r"cari di web|update|compare with news)\b",re.I)


class LinkInput(BaseModel):
    conversation_id:str
    url:str


def grant_for(db,user):
    p=profile(db,user)
    if not has(p,"view_intelligence"):
        raise HTTPException(403,"Active permission to view SmartRadar intelligence is required")
    return p


def needs_tools(cfg,prior,attached):
    q=cfg["question"]
    # Pure follow-up formatting or applying prior work NEVER starts a new
    # public search, including when source-mode permissions made the prior
    # answer unavailable. Disclose that missing context rather than searching.
    if REWRITE.search(q) or APPLY.search(q):
        return False
    if attached and ATTACHMENT_ONLY.search(q) and not NEW_EXTERNAL.search(q):
        return False
    return True


def display(row):
    return {key:row.get(key) for key in (
        "id","type","title","url","resolved_url","read_status","basis",
        "published_at","updated_at","consulted_at","section","reason",
        "reliability","duplicate_of","location_verified","within_period")}


def source_mode_filter(rows,mode,attached):
    return state.filter_evidence(rows,mode,{s["id"] for s in attached})


@router.post("/upload")
async def upload(conversation_id:str=Form(...),file:UploadFile=File(...),
                 user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    raw=await file.read(parsers.MAX_BYTES+1)
    return {"attachment":state.add_file(user,conversation_id,grant,file.filename or "",raw),
            "retention":"IN_PROCESS_UP_TO_12_HOURS"}


@router.post("/link")
def link(body:LinkInput,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return {"attachment":state.add_link(user,body.conversation_id,grant,body.url)}


@router.get("/attachments/{conversation_id}")
def attachments(conversation_id:str,user:User=Depends(current_user),
                db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return {"attachments":state.attachment_list(user,conversation_id,grant),
            "retention":"IN_PROCESS_UP_TO_12_HOURS"}


@router.delete("/attachments/{conversation_id}/{attachment_id}")
def remove_attachment(conversation_id:str,attachment_id:str,
                      user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return state.remove_file(user,conversation_id,grant,attachment_id)


@router.delete("/conversation/{conversation_id}")
def clear(conversation_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    return state.remove_conversation(user,conversation_id,grant)


@router.post("/chat")
def chat(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    cfg=engine.validate(body,grant)
    conversation_id=body.get("conversationId")
    edited_draft=body.get("editedDraft") or ""
    if not isinstance(edited_draft,str) or len(edited_draft)>16000:
        raise HTTPException(422,"Edited draft must be at most 16000 characters")
    if edited_draft and not cfg["reference_turn_id"]:
        raise HTTPException(422,"Edited draft requires a referenced AI-5 turn")
    state.conversation(user,conversation_id,grant,True)
    before=state.turns(user,conversation_id,grant)
    attached=state.attachments_for(user,conversation_id,grant)
    attached_ids={s["id"] for s in attached}
    last=state.latest_relevant(before,cfg["source_mode"],attached_ids)
    if cfg["reference_turn_id"]:
        selected=next((t for t in before if t["turn_id"]==cfg["reference_turn_id"]),None)
        if not selected:raise HTTPException(404,"Referenced AI-5 turn not found")
        if cfg["source_mode"]=="WEB_ONLY" and selected.get("used_saved"):
            raise HTTPException(409,"The referenced turn used saved SmartRadar data. Select a mode that permits it.")
        if cfg["source_mode"]=="SMARTRADAR_ONLY" and selected.get("used_public"):
            raise HTTPException(409,"That turn used live public research. Select a mode permitting public sources.")
        if any(str(src.get("type","")).startswith("ATTACHMENT_") and
               src["id"] not in attached_ids for src in selected.get("sources",[])):
            raise HTTPException(409,"The referenced turn used a removed attachment. Create a new answer first.")
        last=selected
    use_tools=needs_tools(cfg,last,attached)
    key=os.getenv("OPENAI_API_KEY","").strip()
    model=(os.getenv("OPENAI_AI5_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    base=(os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip()
    public={"status":"NOT_SELECTED","sources":[],"as_of":None,"attempts":[]}
    saved=[];warnings=[]
    if cfg["source_mode"]!="SMARTRADAR_ONLY":
        if use_tools:
            public=web.research(cfg["question"],key,model,base,cfg["today"],cfg["recent"])
        elif last:
            kept=source_mode_filter(last.get("sources",[]),cfg["source_mode"],attached)
            prior_public=[r for r in kept if str(r.get("type","")).startswith("PUBLIC_")]
            public={"status":"PRIOR_READ_SNAPSHOT" if prior_public else "NOT_NEEDED",
                    "sources":prior_public,"as_of":last.get("searched_at"),
                    "attempts":[{"phase":"follow-up","status":"PREVIOUSLY_READ",
                                 "discovered":len(prior_public)}]}
        else:public["status"]="NOT_NEEDED"
    if cfg["source_mode"]!="WEB_ONLY":
        if use_tools:
            saved,warnings=saved_research(db,grant,cfg["question"],{
                "smartRadar":True,"legalReferences":True},None)
        elif last:
            saved=[s for s in source_mode_filter(last.get("sources",[]),
                    cfg["source_mode"],attached) if str(s.get("type","")).startswith("SAVED_")]
    if public["status"] not in ("NOT_SELECTED","READ_SOURCES_AVAILABLE",
                               "PRIOR_READ_SNAPSHOT","NOT_NEEDED"):
        warnings.append("Public search unavailable or insufficient ("+public["status"]+
                        "); no internal records were substituted for a Web-only request.")
    if public["status"]=="PRIOR_READ_SNAPSHOT":
        warnings.append("This revision uses earlier read public pages; no new search was run.")
    if not use_tools and not last and before:
        warnings.append("Earlier material is unavailable under this source setting. "
                        "Switch back to a permitted source mode or provide a redacted excerpt.")
    if not use_tools and last:
        # Preserve manually provided file/link content (active only), and
        # sources from the referenced result rather than creating new links.
        relevant=source_mode_filter(last.get("sources",[]),cfg["source_mode"],attached)
        base_sources=relevant+[s for s in attached if s["id"] not in
                               {x["id"] for x in relevant}]
    else:
        base_sources=[*public["sources"],*saved,*attached]
    combined=source_mode_filter(base_sources,cfg["source_mode"],attached)
    history=state.history_context(before,cfg["source_mode"],attached_ids)
    if cfg["reference_turn_id"] and last and last not in before[-7:]:
        history.append({"question":last["question"],
                        "answer":str(last["answer"].get("body") or "")[:3500],
                        "draft":str(last["answer"].get("draft") or "")[:2200],
                        "open_questions":(last["answer"].get("open_questions") or [])[:4],
                        "comparison":(last["answer"].get("table") or {}).get("rows",[])[:6],
                        "source_ids":[x["id"] for x in combined][:16],
                        "mode":last.get("mode")})
    if edited_draft:
        history.append({"question":"User-edited previous draft, not a new factual source",
                        "draft":edited_draft,
                        "source_ids":[x["id"] for x in combined][:16],
                        "mode":last.get("mode") if last else "GENERAL_RESEARCH"})
    generated,status=engine.generate(cfg,history,combined,public["status"],
                                     profile_context(grant),key,model,base)
    answer=engine.sanitize(generated,combined,cfg,public["status"])
    if status!="COMPLETE":
        warnings.append("AI-5 answer generation is unavailable ("+status+
                        "); no fabricated source-based reply was substituted.")
    turn_id=secrets.token_hex(16)
    record={"turn_id":turn_id,"question":cfg["question"],"mode":cfg["mode"],
            "action_mode":cfg["action_mode"],"source_mode":cfg["source_mode"],
            "answer":answer,"sources":combined[:40],"used_saved":bool(saved),
            "used_public":bool(public.get("sources")),"searched_at":public.get("as_of"),
            "created_at":datetime.now(timezone.utc).isoformat()}
    state.add_turn(user,conversation_id,grant,record)
    trail={"sources":[display(s) for s in combined[:40]],
           "public_status":public["status"],"searched_at":public.get("as_of"),
           "attempts":public.get("attempts",[]),
           "read_public_count":sum(x.get("read_status")=="READ" and
                         str(x.get("type","")).startswith("PUBLIC_") for x in combined),
           "saved_count":sum(str(x.get("type","")).startswith("SAVED_") for x in combined),
           "attachment_count":sum(str(x.get("type","")).startswith("ATTACHMENT_") for x in combined),
           "warnings":warnings,"retention":"IN_PROCESS_UP_TO_12_HOURS"}
    return {"assistant":"AI-5","turn_id":turn_id,"conversation_id":conversation_id,
            "mode":cfg["mode"],"action_mode":cfg["action_mode"],
            "source_mode":cfg["source_mode"],"answer":answer,
            "research_trail":trail,"synthesis_status":status,
            "actions_executed":False}


@router.post("/export/{file_type}")
def download(file_type:str,body:dict,user:User=Depends(current_user),
             db:Session=Depends(get_db)):
    grant=grant_for(db,user)
    if file_type not in export.MIME:raise HTTPException(422,"Use pdf, docx or xlsx")
    conversation_id=body.get("conversationId")
    row=state.get_turn(user,conversation_id,grant,body.get("turnId"))
    mode=body.get("sourceMode")
    if mode!=row["source_mode"]:
        raise HTTPException(409,"For this export, reselect the source mode used to generate this answer.")
    current_ids={a["id"] for a in state.attachments_for(user,conversation_id,grant)}
    removed=[s["id"] for s in row["sources"]
             if str(s.get("type","")).startswith("ATTACHMENT_")
             and s["id"] not in current_ids]
    if removed:
        raise HTTPException(409,"An attachment was removed. Generate an updated answer before exporting.")
    edited=body.get("editedText") or ""
    try:
        payload,mime,filename=export.create(row,file_type,edited)
    except (ValueError,TypeError) as ex:
        raise HTTPException(422,str(ex)[:120]) from ex
    except Exception:
        LOG.exception("AI5_EXPORT_FAILED type=%s",file_type)
        raise HTTPException(503,"Export unavailable; your conversation remains saved. Retry without losing your work.")
    return StreamingResponse(io.BytesIO(payload),media_type=mime,
             headers={"Content-Disposition":'attachment; filename="'+filename+'"',
                      "Cache-Control":"private, no-store",
                      "X-Content-Type-Options":"nosniff"})
