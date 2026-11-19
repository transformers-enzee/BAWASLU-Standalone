"""Read-only, ownership- and evidence-scoped replay of existing Assistant replies.

Never generates answers, claims authenticated model provenance, or accepts a
source excerpt from the client. History is user-editable; stored text is not
independent evidence or human accuracy.
"""
import json
import re
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException,Response,Query
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .models import User
from .access import profile,has
from .assistant_history import AssistantThread
from .assistant_eval_sampling import MixedAnswerAuditRequest,resolve_mixed_audit_sources,build_mixed_answer_audit
from .assistant_saved_reply_human_packet import build_authorized_saved_reply_review_packet
from .assistant_saved_reply_response_triage import (
    summarize_authorized_saved_reply_audit,
    summarize_authorized_saved_reply_batch,
)

router=APIRouter(prefix="/api/assistant-evaluation",tags=["assistant-evaluation"])
_EXACT_REF=re.compile(r"^(?:SOCIAL-[1-9][0-9]{0,11}|INT-[A-Za-z0-9:_-]{1,80}|DOC-[1-9][0-9]{0,11}-P[1-9][0-9]{0,7})$")
_DISPLAY_REF=re.compile(r"\[((?:SOCIAL|INT)-[A-Za-z0-9:_-]+|DOC-[0-9]+-P[0-9]+)\]")
MAX_SOURCE_CARDS=12
MAX_REPLAY_SOURCE_IDS=20

class SavedReplyAuditRequest(BaseModel):
    thread_id:str=Field(min_length=36,max_length=36)
    answer_message_index:int=Field(ge=1,le=59)

class BatchSavedReplyAuditRequest(BaseModel):
    selections:list[SavedReplyAuditRequest]=Field(min_length=1,max_length=5)

class SavedReplyReviewerRating(BaseModel):
    model_config=ConfigDict(extra="forbid")
    thread_id:str=Field(min_length=36,max_length=36)
    answer_message_index:int=Field(ge=1,le=59)
    ratings:dict[str,str]=Field(min_length=1,max_length=6)
    original_answer_reviewed:bool=False
    independent_review_attested:bool=False

class SavedReplyHumanReviewRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    selections:list[SavedReplyAuditRequest]=Field(min_length=1,max_length=5)
    submissions:list[SavedReplyReviewerRating]=Field(min_length=0,max_length=5)

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
    displayed=list(dict.fromkeys(_DISPLAY_REF.findall(text)))
    if cards is not None and not isinstance(cards,list):
        return {"eligible":False,"reason_code":"INVALID_SAVED_EVIDENCE_CARDS",
                "source_ids":[],"cited_count":len(displayed)}
    cards=cards or []
    if len(cards)>MAX_SOURCE_CARDS:
        return {"eligible":False,"reason_code":"SAVED_EVIDENCE_SCOPE_EXCEEDS_LIMIT",
                "source_ids":[],"cited_count":len(displayed)}
    identifiers=[]
    for card in cards:
        identifier=_source_id(card)
        if not identifier:
            return {"eligible":False,"reason_code":"UNSUPPORTED_SAVED_SOURCE_IDENTIFIER",
                    "source_ids":[],"cited_count":len(displayed)}
        if identifier not in identifiers:identifiers.append(identifier)
    # Saved source cards are a contextual shortlist and may omit a valid
    # source ID that the answer explicitly cites. We must reauthorize EVERY
    # displayed ID, never call an omitted cited ID forged without checking it.
    # Malformed references are also rejected; an answer cannot silently
    # escape source authorization through an invalid citation spelling.
    if any(not _EXACT_REF.fullmatch(ref) for ref in displayed):
        return {"eligible":False,"reason_code":"INVALID_DISPLAYED_SOURCE_REFERENCE",
                "source_ids":[],"cited_count":len(displayed)}
    cited_only=[ref for ref in displayed if ref not in identifiers]
    identifiers.extend(cited_only)
    if not identifiers:
        return {"eligible":False,"reason_code":"NO_SAVED_EVIDENCE_CARDS_OR_CITATIONS",
                "source_ids":[],"cited_count":0}
    if len(identifiers)>MAX_REPLAY_SOURCE_IDS:
        return {"eligible":False,"reason_code":"COMBINED_SOURCE_SCOPE_EXCEEDS_LIMIT",
                "source_ids":[],"cited_count":len(displayed)}
    return {"eligible":True,"reason_code":"AUTHORIZATION_RECHECK_REQUIRED",
            "source_ids":identifiers,"cited_count":len(displayed),
            "contextual_card_count":len(cards),
            "cited_only_source_count":len(cited_only),
            "replay_scope":"SAVED_CARDS_PLUS_EXPLICIT_CITATIONS"}

def _historical_citation_coverage(scope):
    """Attribution format diagnostic only, never an accuracy verdict."""
    cards=scope.get("contextual_card_count",0)
    cited=scope.get("cited_count",0)
    cited_only=scope.get("cited_only_source_count",0)
    if cards and not cited:
        return "SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS"
    if cited_only and cards:
        return "DISPLAYED_CITATIONS_MISSING_FROM_SAVED_CARDS"
    if cited_only:
        return "DISPLAYED_CITATIONS_WITHOUT_SAVED_CARDS"
    return "DISPLAYED_CITATIONS_WITH_SAVED_CARDS"

def _historical_review_route(status,coverage=None,issue_count=0):
    """Officer guidance only: never assign accuracy, legal or acceptance status."""
    if status=="SOURCE_UNAVAILABLE":
        return "RECHECK_CURRENT_EVIDENCE_ACCESS"
    if status=="UNAVAILABLE":
        return "VERIFY_OWNED_HISTORY_SELECTION"
    if status=="INELIGIBLE":
        return "INSPECT_HISTORY_FORMAT_MANUALLY"
    if status!="AUDITED":
        return "NO_AUTOMATED_REVIEW_ROUTE"
    if coverage!="DISPLAYED_CITATIONS_WITH_SAVED_CARDS":
        return "REVIEW_CITATION_ATTRIBUTION"
    if issue_count>0:
        return "REVIEW_FLAGGED_CLAIMS_WITH_SOURCES"
    return "HUMAN_EVIDENCE_SPOT_CHECK"


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
                "cited_only_source_count":scoped.get("cited_only_source_count",0),
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
        "cited_only_source_count":scope.get("cited_only_source_count",0),
        "historical_citation_coverage":_historical_citation_coverage(scope),
        "review_route":_historical_review_route(
            "AUDITED",_historical_citation_coverage(scope),
            result["issue_triage"]["issue_candidate_count"]),
        "review_route_is_suggestion_only":True,
        "audit":result,
        "response_quality_triage":summarize_authorized_saved_reply_audit(result),
        "human_accuracy":None,"factual_accuracy_verified":False,
        "legal_signoff_verified":False,"client_acceptance_verified":False,
        "saved_thread_modified":False,"model_calls":0,"database_writes":0
    }


def audit_owned_saved_reply_batch(db,principal,user_id,selections):
    """Bounded, exact, permission-checked replay; no persisted QA scores.

    Every result is explicit: audited, ineligible, or source unavailable.
    Fail an unauthorized thread as unavailable, without exposing whether a
    thread belonging to somebody else actually exists.
    """
    if not selections or len(selections)>5:
        raise HTTPException(422,"Select between one and five saved replies")
    keys=[(item.thread_id,item.answer_message_index) for item in selections]
    if len(set(keys))!=len(keys):
        raise HTTPException(422,"Duplicate saved reply selection")
    thread_ids=list(dict.fromkeys(item.thread_id for item in selections))
    rows=db.query(AssistantThread).filter(
        AssistantThread.user_id==user_id,
        AssistantThread.id.in_(thread_ids)).all()
    own={row.id:row for row in rows}
    # Per-request scoped inventory, not a cross-user or persistent cache.
    batch_principal={**principal,"_assistant_eval_batch_cache":{}} if isinstance(principal,dict) else principal
    output=[]
    totals=Counter()
    issue_categories=Counter()
    for selection in selections:
        item={"thread_id":selection.thread_id,
              "answer_message_index":selection.answer_message_index}
        row=own.get(selection.thread_id)
        if row is None:
            item.update(status="UNAVAILABLE",
                        reason_code="SAVED_CONVERSATION_UNAVAILABLE")
        else:
            try:
                messages=_read_messages(row)
                scope=_reply_scope(messages,selection.answer_message_index)
                if not scope["eligible"]:
                    item.update(status="INELIGIBLE",reason_code=scope["reason_code"])
                else:
                    audit=MixedAnswerAuditRequest(
                        source_ids=scope["source_ids"],
                        question=messages[selection.answer_message_index-1]["text"],
                        answer=messages[selection.answer_message_index]["text"])
                    sources=resolve_mixed_audit_sources(db,batch_principal,audit)
                    result=build_mixed_answer_audit(sources,audit)
                    triage=result["issue_triage"]
                    cats=triage.get("issue_category_counts") or {}
                    issue_categories.update({k:int(v) for k,v in cats.items()
                                             if k in (
                                                 "CITATION_INTEGRITY",
                                                 "CROSS_MODULE_COVERAGE",
                                                 "SOURCE_RELEVANCE",
                                                 "LEGAL_SCOPE_REVIEW",
                                                 "PLATFORM_POLICY_AUTHORITY",
                                                 "FORMAL_DECISION_PROVENANCE",
                                                 "HUMAN_EVIDENCE_VERIFICATION")})
                    item.update(status="AUDITED",
                        reason_code="DETERMINISTIC_SOURCE_REVIEW_ONLY",
                        source_count=len(sources),
                        cited_only_source_count=scope.get("cited_only_source_count",0),
                        historical_citation_coverage=_historical_citation_coverage(scope),
                        cited_count=len(result["cited_authorized_ids"]),
                        missing_source_types=result["missing_cited_source_kinds"],
                        issue_candidate_count=triage["issue_candidate_count"],
                        issue_category_counts=cats,
                        selected_source_kinds=result["selected_source_kinds"],
                        source_record_ids=result["source_record_ids"],
                        # A reduced, allowlisted result supports intentional local
                        # issue-register capture without exporting original content.
                        issue_triage=triage,
                        response_quality_triage=summarize_authorized_saved_reply_audit(result))
            except HTTPException as exc:
                # Not exposing authorization differences between hidden sources.
                if exc.status_code in (403,404):
                    item.update(status="SOURCE_UNAVAILABLE",
                                reason_code="CURRENT_SOURCE_ACCESS_OR_PRESENCE")
                elif exc.status_code in (409,422):
                    item.update(status="INELIGIBLE",
                                reason_code="SOURCE_CONSISTENCY_OR_INPUT")
                else:
                    raise
        item["review_route"]=_historical_review_route(
            item["status"],item.get("historical_citation_coverage"),
            item.get("issue_candidate_count",0))
        totals[item["status"]]+=1
        output.append(item)
    result={"schema":"BAWASLU_SAVED_REPLY_BATCH_AUDIT_V1618",
            "requested":len(selections),
            "audited":totals["AUDITED"],
            "ineligible":totals["INELIGIBLE"],
            "unavailable":totals["UNAVAILABLE"]+totals["SOURCE_UNAVAILABLE"],
            "unavailable_source":totals["SOURCE_UNAVAILABLE"],
            "results":output,
            "response_quality_batch_triage":summarize_authorized_saved_reply_batch(output),
            "reason_code_counts":dict(sorted(Counter(
                x["reason_code"] for x in output if x["status"]!="AUDITED"
            ).items())),
            "selection_method":"EXPLICIT_USER_SELECTED_REPLIES",
            "selected_reply_count":len(selections),
            "batch_is_representative":False,
            "issue_category_occurrences":dict(sorted(issue_categories.items())),
            "saved_cards_without_displayed_citations":sum(
                x.get("historical_citation_coverage")=="SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS"
                for x in output if x["status"]=="AUDITED"),
            "citation_coverage_counts":dict(sorted(Counter(
                x["historical_citation_coverage"] for x in output
                if x["status"]=="AUDITED"
            ).items())),
            "source_unavailable_review_count":totals["SOURCE_UNAVAILABLE"],
            "citation_coverage_is_format_diagnostic_only":True,
            "review_route_counts":dict(sorted(Counter(
                x["review_route"] for x in output).items())),
            "review_routes_are_unverified_suggestions":True,
            "batch_scoped_evidence_cache_only":True,
            "issue_counts_are_unverified_diagnostic_occurrences":True,
            "selection_not_random_or_representative":True,
            "real_model_generation_provenance_verified":False,
            "source_truth_verified":False,
            "human_accuracy":None,"human_verified_errors":0,
            "legal_signoff_verified":False,
            "formal_client_acceptance_verified":False,
            "answers_generated":0,"database_writes":0,
            "saved_replies_modified":False}
    result["human_review_packet"]=build_authorized_saved_reply_review_packet(result)
    return result


@router.post("/saved-reply-batch-audit")
def saved_reply_batch_audit(
    request:BatchSavedReplyAuditRequest,response:Response,
    user:User=Depends(current_user),db:Session=Depends(get_db)
):
    principal=_access(db,user)
    _no_store(response)
    return audit_owned_saved_reply_batch(
        db,principal,user.id,request.selections)

@router.post("/saved-reply-human-review")
def saved_reply_human_review(
    request:SavedReplyHumanReviewRequest,response:Response,
    user:User=Depends(current_user),db:Session=Depends(get_db)
):
    """Admin-only, read-only human scoring after fresh saved-source authorization.

    A successful invocation merely reports self-attested review counts; no
    accuracy, legal decision, reviewer identity, or client approval is verified.
    """
    principal=_access(db,user)
    if not has(principal,"administration"):
        raise HTTPException(403,"Administrator review access required")
    _no_store(response)
    batch=audit_owned_saved_reply_batch(
        db,principal,user.id,request.selections)
    packet=batch["human_review_packet"]
    # Never accept client-supplied historical evidence or access flags.
    # The new batch run has already reauthorized each selected reply.
    from .assistant_human_review_scoring import compile_human_review_scores
    submitted=[]
    for row in request.submissions:
        data=row.model_dump()
        data["source_access_rechecked"]=True
        submitted.append(data)
    if not packet["items"]:
        raise HTTPException(422,"No selected replies are eligible for human review")
    try:
        scores=compile_human_review_scores(packet,submitted)
    except ValueError:
        raise HTTPException(422,"Invalid review selections or ratings")
    return {
        "schema":"BAWASLU_SAVED_REPLY_HUMAN_REVIEW_V17501",
        "scores":scores,
        "selected_reply_count":len(request.selections),
        "eligible_reply_count":len(packet["items"]),
        "source_access_reauthorized_during_request":True,
        "reviewer_attestations_not_independently_verified":True,
        "actual_model_accuracy":None,
        "human_review_is_formal_legal_signoff":False,
        "released_approved":False,
        "review_data_persisted":False,
        "model_calls":0,"database_writes":0,
    }
