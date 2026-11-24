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
        "reliability","duplicate_of","location_verified","within_period",
        "search_dimensions","document_type")}


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
    cfg["evidence_intent"]=web.evidence_intent(cfg["question"])
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
    cfg["research_dimensions"]=public.get("dimensions",[])
    cfg["research_coverage"]=public.get("coverage",[])

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
    answer_audit={"status":"NOT_RUN","items":[],"missing_requests":[]}
    # An independent completeness pass prevents the synthesis model from silently
    # abandoning individual parts of a broad user question.
    multi_part=len(cfg.get("research_dimensions") or [])>1 or bool(web.BROAD.search(cfg["question"]))
    if use_tools and key and multi_part and status=="COMPLETE":
        answer_audit=engine.review_scope(cfg,generated,key,model,base)
        missing_evidence=answer_audit.get("missing_requests") or []
        buried_findings=engine.main_answer_evidence_gaps(generated)
        unused_observations=engine.undiscussed_comparative_observations(
            cfg,generated,combined)
        missing=list(dict.fromkeys(
            missing_evidence+buried_findings+unused_observations))
        if missing:
            # If the model already received the evidence but relegated useful
            # figures to caveats, rewrite first: no redundant paid search.
            if cfg["source_mode"]!="SMARTRADAR_ONLY" and missing_evidence:
                known={str(s.get("url") or "").split("#")[0] for s in combined}
                rescue=web.fill_answer_gaps(cfg["question"],missing_evidence,key,model,base,
                                            cfg["today"],known)
                public["attempts"].extend(rescue.get("attempts",[]))
                fresh=rescue.get("sources") or []
                public["sources"].extend(fresh)
                selected={str(r.get("url") or "").split("#")[0]:r for r in fresh}
                for attempt in rescue.get("attempts",[]):
                    for lead in attempt.get("leads",[]):
                        page=selected.get(str(lead.get("url") or "").split("#")[0])
                        lead["selected"]=bool(page)
                        lead["read_status"]=page.get("read_status","UNKNOWN") if page else "NOT_READ"
                        lead["reason"]=(page.get("reason","") if page else
                            "Not opened: duplicate or bounded page selection")
                # Newly discovered evidence must reach the revised answer model
                # before older, less relevant pages exhaust its 34-source budget.
                combined=source_mode_filter([*fresh,*combined],cfg["source_mode"],attached)
                if fresh and cfg.get("research_dimensions"):
                    cfg["research_coverage"]=web.evaluate_coverage(
                        cfg["research_dimensions"],public["sources"],key,model,base)
                    public["coverage"]=cfg["research_coverage"]
            cfg["answer_revision"]={
                "unanswered_parts_to_address_or_explicitly_disclose":missing,
                "previous_draft_to_rewrite_in_full_not_cite_as_evidence":
                    engine._answer_text(generated)[:9000]}
            revised,revision_status=engine.generate(cfg,history,combined,
                                   public["status"],profile_context(grant),
                                   key,model,base)
            if revision_status=="COMPLETE":
                generated=revised
                answer_audit=engine.review_scope(cfg,generated,key,model,base)
                buried=(engine.main_answer_evidence_gaps(generated)+
                        engine.undiscussed_comparative_observations(
                            cfg,generated,combined))
                if buried:
                    answer_audit["status"]="GAPS_FOUND"
                    answer_audit["missing_requests"]=list(dict.fromkeys(
                        (answer_audit.get("missing_requests") or [])+buried))
            else:
                warnings.append("Completeness revision unavailable ("+
                                revision_status+"); retaining first answer.")
    evidence_trace=engine.model_trace(cfg,combined)
    incomplete=[r["name"] for r in cfg["research_coverage"]
                if r.get("status")!="COVERED"]
    if incomplete:
        warnings.append("Research coverage remains incomplete: "+", ".join(incomplete[:6]))
    answer=engine.sanitize(generated,combined,cfg,public["status"])
    if answer_audit.get("status")=="GAPS_FOUND":
        gaps=answer_audit.get("missing_requests") or []
        warnings.append("Some requested answer sections remain incomplete: "+
                        "; ".join(gaps[:5]))
        for part in gaps[:4]:
            note="Unresolved request: "+part
            if note not in answer["open_questions"]:
                answer["open_questions"].append(note)
    if status!="COMPLETE":
        warnings.append("AI-5 answer generation is unavailable ("+status+
                        "); no fabricated source-based reply was substituted.")
    turn_id=secrets.token_hex(16)
    record={"turn_id":turn_id,"question":cfg["question"],"mode":cfg["mode"],
            "action_mode":cfg["action_mode"],"source_mode":cfg["source_mode"],
            "answer":answer,"sources":combined[:40],"used_saved":bool(saved),
            "used_public":bool(public.get("sources")),"searched_at":public.get("as_of"),
            "research_trace":{"attempts":public.get("attempts",[])[:32],
                "dimensions":cfg.get("research_dimensions",[])[:8],
                "coverage":cfg.get("research_coverage",[])[:8],
                "evidence_intent":cfg.get("evidence_intent"),
                "budget":public.get("budget",{}),
                "model_source_ids":evidence_trace["source_ids"],
                "cited_source_ids":sorted(set(engine.SOURCE_TAG.findall(
                    "\n".join([answer.get("body",""),answer.get("draft",""),
                    str(answer.get("table",{})),
                    " ".join(answer.get("open_questions") or [])])))),
                "model_passages":evidence_trace["passages"],
                "excluded_source_ids":evidence_trace["excluded_source_ids"],
                "answer_audit":answer_audit},
            "created_at":datetime.now(timezone.utc).isoformat()}
    state.add_turn(user,conversation_id,grant,record)
    trail={"sources":[display(s) for s in combined[:40]],
           "public_status":public["status"],"searched_at":public.get("as_of"),
           "attempts":public.get("attempts",[]),
           "requested_dimensions":cfg.get("research_dimensions",[]),
           "coverage":cfg.get("research_coverage",[]),
           "evidence_intent":cfg.get("evidence_intent"),
           "budget":public.get("budget",{}),
           "model_passages":evidence_trace["passages"],
           "excluded_source_ids":evidence_trace["excluded_source_ids"],
           "answer_audit":answer_audit,
           "model_source_ids":evidence_trace["source_ids"],
           "cited_source_ids":sorted(set(engine.SOURCE_TAG.findall(
               "\n".join([answer.get("body",""),answer.get("draft",""),
               str(answer.get("table",{})),
               " ".join(answer.get("open_questions") or [])])))),
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
        include_trail=body.get("includeResearchTrail",False)
        if type(include_trail) is not bool:
            raise ValueError("includeResearchTrail must be a boolean")
        if include_trail and file_type=="pdf":
            payload,mime,filename=export.create(
                row,file_type,edited,include_research_trail=True)
        else:
            # Preserve the stable, three-argument export contract for
            # existing clients and failure-handling regression fixtures.
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
