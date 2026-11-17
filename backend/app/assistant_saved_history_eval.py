"""Read-only, ownership- and evidence-scoped replay of existing Assistant replies.

Never generates answers, claims authenticated model provenance, or accepts a
source excerpt from the client. History is user-editable; stored text is not
independent evidence or human accuracy.
"""
import json
import re
from fastapi import APIRouter,Depends,HTTPException,Response,Query
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .models import User
from .access import profile,has
from .assistant_history import AssistantThread
from .assistant_eval_sampling import MixedAnswerAuditRequest,resolve_mixed_audit_sources,build_mixed_answer_audit

router=APIRouter(prefix="/api/assistant-evaluation",tags=["assistant-evaluation"])
_EXACT_REF=re.compile(r"^(?:SOCIAL-[1-9][0-9]{0,11}|INT-[A-Za-z0-9:_-]{1,80}|DOC-[1-9][0-9]{0,11}-P[1-9][0-9]{0,7})$")
_DISPLAY_REF=re.compile(r"\[((?:SOCIAL|INT)-[A-Za-z0-9:_-]+|DOC-[0-9]+-P[0-9]+)\]")
MAX_SOURCE_CARDS=12

class SavedReplyAuditRequest(BaseModel):
    thread_id:str=Field(min_length=36,max_length=36)
    answer_message_index:int=Field(ge=1,le=59)

def _access(db,user):
    principal=profile(db,user)
    if principal.get("status")!="Active" or not has(principal,"view_intelligence"):
        raise HTTPException(403,"Active intelligence access required")
    return principal

def _read_messages(row):
    try:
        value=json.loads(row.messages_json or "[]")
    except (TypeError,ValueError):
        raise HTTPException(422,"Saved conversation format unavailable")
    if not isinstance(value,list) or len(value)>60:
        raise HTTPException(422,"Saved conversation format unavailable")
    return value

def _source_id(row):
    if not isinstance(row,dict):return None
    # Historical social cards use id/intelligence_id; PDF pages use record_id.
    # These are only client-owned snapshots: reauthorize every ID against fresh
    # saved Inbox, formal intelligence, or active PDF before any evaluation.
    values=[row.get("record_id"),row.get("id"),row.get("intelligence_id")]
    for value in values:
        if isinstance(value,str) and _EXACT_REF.fullmatch(value):
            return value
    return None

def _reply_scope(messages,index):
    if not isinstance(index,int) or index<1 or index>=len(messages):
        return {"eligible":False,"reason_code":"INVALID_ANSWER_TURN","source_ids":[],"cited_count":0}
    answer=messages[index]
    preceding=messages[index-1]
    if (not isinstance(answer,dict) or not isinstance(preceding,dict)
        or answer.get("role")!="assistant" or preceding.get("role")!="user"):
        return {"eligible":False,"reason_code":"NO_ADJACENT_USER_QUESTION","source_ids":[],"cited_count":0}
    text=answer.get("text")
    question=preceding.get("text")
    if not isinstance(text,str) or not isinstance(question,str) or not (3<=len(text)<=10000) or not (3<=len(question)<=1200):
        return {"eligible":False,"reason_code":"ANSWER_OR_QUESTION_LENGTH_UNSUPPORTED","source_ids":[],"cited_count":0}
    cards=answer.get("records")
    if not isinstance(cards,list) or not cards:
        return {"eligible":False,"reason_code":"NO_SAVED_EVIDENCE_CARDS","source_ids":[],"cited_count":len(_DISPLAY_REF.findall(text))}
    if len(cards)>12:
        return {"eligible":False,"reason_code":"SAVED_EVIDENCE_SCOPE_EXCEEDS_LIMIT","source_ids":[],"cited_count":len(_DISPLAY_REF.findall(text))}
    identifiers=[]
    for card in cards:
        identifier=_source_id(card)
        if not identifier:
            return {"eligible":False,"reason_code":"UNSUPPORTED_SAVED_SOURCE_IDENTIFIER","source_ids":[],"cited_count":len(_DISPLAY_REF.findall(text))}
        if identifier not in identifiers:identifiers.append(identifier)
    if len(identifiers)>MAX_SOURCE_CARDS:
        return {"eligible":False,"reason_code":"SAVED_EVIDENCE_SCOPE_EXCEEDS_LIMIT","source_ids":[],"cited_count":len(_DISPLAY_REF.findall(text))}
    return {"eligible":True,"reason_code":"AUTHORIZATION_RECHECK_REQUIRED",
            "source_ids":identifiers,"cited_count":len(set(_DISPLAY_REF.findall(text)))}

def _no_store(response):
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Evaluation-Generation"]="NONE"
    response.headers["X-Acceptance-Status"]="PENDING_HUMAN_REVIEW"

@router.get("/saved-reply-candidates")
def saved_reply_candidates(
    response:Response,limit:int=Query(default=40,ge=1,le=40),
    user:User=Depends(current_user),db:Session=Depends(get_db)
):
    _access(db,user)
    _no_store(response)
    threads=db.query(AssistantThread).filter(
        AssistantThread.user_id==user.id).order_by(
        AssistantThread.updated_at.desc()).limit(limit).all()
    candidates=[]
    for row in threads:
        try:messages=_read_messages(row)
        except HTTPException:continue
        for index,msg in enumerate(messages):
            if not isinstance(msg,dict) or msg.get("role")!="assistant":continue
            scoped=_reply_scope(messages,index)
            candidates.append({"thread_id":row.id,"answer_message_index":index,
                "thread_updated_at":row.updated_at.isoformat(),
                "saved_source_count":len(scoped["source_ids"]),
                "displayed_citation_count":scoped["cited_count"],
                "eligible":scoped["eligible"],"reason_code":scoped["reason_code"],
                "current_source_permissions_rechecked":False})
            if len(candidates)>=120:break
        if len(candidates)>=120:break
    return {"schema":"BAWASLU_SAVED_REPLY_CANDIDATES_V1616",
            "candidates":candidates,"candidate_count":len(candidates),
            "eligible_count":sum(x["eligible"] for x in candidates),
            "history_owned_by_current_user":True,
            "includes_answer_text":False,"includes_question_text":False,
            "source_permission_rechecked_at_listing":False,
            "model_answers_generated":0,"database_writes":0,
            "human_accuracy_measured":False}

@router.post("/saved-reply-audit")
def saved_reply_audit(
    request:SavedReplyAuditRequest,response:Response,
    user:User=Depends(current_user),db:Session=Depends(get_db)
):
    principal=_access(db,user)
    _no_store(response)
    row=db.query(AssistantThread).filter(
        AssistantThread.id==request.thread_id,
        AssistantThread.user_id==user.id).first()
    if row is None:
        raise HTTPException(404,"Saved conversation unavailable")
    messages=_read_messages(row)
    scope=_reply_scope(messages,request.answer_message_index)
    if not scope["eligible"]:
        raise HTTPException(422,"Saved answer cannot be audited: "+scope["reason_code"])
    answer=messages[request.answer_message_index]
    question=messages[request.answer_message_index-1]
    audit=MixedAnswerAuditRequest(
        source_ids=scope["source_ids"],question=question["text"],answer=answer["text"])
    # Reauthorizes every selected historical card against LIVE permission scope
    # and active, exact references; no historical source text is used as truth.
    evidence=resolve_mixed_audit_sources(db,principal,audit)
    result=build_mixed_answer_audit(evidence,audit)
    return {
        "schema":"BAWASLU_SAVED_REPLY_AUDIT_V1616",
        "thread_id":request.thread_id,
        "answer_message_index":request.answer_message_index,
        "history_record_was_saved":True,
        "original_model_generation_provenance_verified":False,
        "history_content_user_editable":True,
        "all_saved_source_ids_reauthorized":True,
        "fresh_source_scope_count":len(evidence),
        "audit":result,
        "human_accuracy":None,"factual_accuracy_verified":False,
        "legal_signoff_verified":False,"client_acceptance_verified":False,
        "saved_thread_modified":False,"model_calls":0,"database_writes":0
    }
