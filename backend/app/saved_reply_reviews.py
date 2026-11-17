"""Persistent owned Assistant review progress, separate from legal acceptance."""
import json, hashlib
from datetime import datetime
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy import Integer,String,DateTime,Boolean,ForeignKey,UniqueConstraint,update
from sqlalchemy.orm import Mapped,mapped_column,Session
from .db import Base,get_db
from .auth import current_user
from .models import User
from .access import profile,has
from .assistant_history import AssistantThread
from .assistant_saved_history_eval import _reply_scope,_read_messages,_historical_citation_coverage,_historical_review_route
from .assistant_eval_sampling import MixedAnswerAuditRequest,resolve_mixed_audit_sources,build_mixed_answer_audit

router=APIRouter(prefix="/api/assistant-evaluation/saved-reply-reviews",tags=["assistant-evaluation"])
STATES={"PENDING_REVIEW","EVIDENCE_CHECK_IN_PROGRESS","REVIEW_BLOCKED","EVIDENCE_CHECKED_FOLLOWUP_NEEDED","EVIDENCE_CHECKED_NO_FURTHER_ACTION"}
COMPLETE={"EVIDENCE_CHECKED_FOLLOWUP_NEEDED","EVIDENCE_CHECKED_NO_FURTHER_ACTION"}

class SavedReplyReview(Base):
 __tablename__="assistant_saved_reply_reviews"
 __table_args__=(UniqueConstraint("owner_id","thread_id","answer_message_index",name="uq_saved_reply_review_owner_turn"),)
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 owner_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),index=True,nullable=False)
 thread_id:Mapped[str]=mapped_column(String(36),index=True,nullable=False)
 answer_message_index:Mapped[int]=mapped_column(Integer,nullable=False)
 reply_fingerprint:Mapped[str]=mapped_column(String(64),nullable=False)
 review_state:Mapped[str]=mapped_column(String(60),nullable=False)
 evidence_checked:Mapped[bool]=mapped_column(Boolean,nullable=False)
 reviewer_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False)
 review_route:Mapped[str]=mapped_column(String(80),nullable=False)
 version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
 created_at:Mapped[datetime]=mapped_column(DateTime,nullable=False,default=datetime.utcnow)
 updated_at:Mapped[datetime]=mapped_column(DateTime,nullable=False,default=datetime.utcnow)

class SavedReplyReviewEvent(Base):
 __tablename__="assistant_saved_reply_review_events"
 id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
 review_id:Mapped[int]=mapped_column(Integer,ForeignKey("assistant_saved_reply_reviews.id"),index=True,nullable=False)
 actor_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False)
 from_state:Mapped[str]=mapped_column(String(60),nullable=False)
 to_state:Mapped[str]=mapped_column(String(60),nullable=False)
 version:Mapped[int]=mapped_column(Integer,nullable=False)
 at:Mapped[datetime]=mapped_column(DateTime,nullable=False,default=datetime.utcnow)

class ReviewSave(BaseModel):
 thread_id:str=Field(min_length=36,max_length=36)
 answer_message_index:int=Field(ge=1,le=59)
 review_state:str
 evidence_checked:bool=False
 expected_version:int=Field(ge=0,le=1000000)

def _gate(db,user):
 p=profile(db,user)
 if not has(p,"view_intelligence") or not has(p,"review_ai_suggestions"):
  raise HTTPException(403,"Active reviewer permission required")
 return p

def _owned(db,user,thread,index):
 row=db.query(AssistantThread).filter(AssistantThread.id==thread,AssistantThread.user_id==user.id).first()
 if row is None:raise HTTPException(404,"Saved conversation unavailable")
 messages=_read_messages(row)
 scope=_reply_scope(messages,index)
 if not scope["eligible"]:raise HTTPException(422,"Saved reply is not eligible for review")
 pair=messages[index-1:index+1]
 stamp=hashlib.sha256(json.dumps(pair,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
 return pair,scope,stamp

def _attention(state):
 if state=="RECHECK_SAVED_REPLY":return "RECHECK_CHANGED_ANSWER"
 if state=="EVIDENCE_CHECKED_FOLLOWUP_NEEDED":return "FOLLOW_UP_REQUIRED"
 if state=="EVIDENCE_CHECKED_NO_FURTHER_ACTION":return "NO_FURTHER_ACTION_PROPOSED"
 if state=="REVIEW_BLOCKED":return "RESOLVE_REVIEW_BLOCKER"
 return "CONTINUE_REVIEW"

def _output(x,stale=False):
 return {"thread_id":x.thread_id,"answer_message_index":x.answer_message_index,
 "review_state":x.review_state,"evidence_checked":x.evidence_checked,
 "reviewer_id":x.reviewer_id,"review_route":x.review_route,
 "version":x.version,"updated_at":x.updated_at.isoformat(),"saved_reply_changed":stale,
 "effective_review_state":"RECHECK_SAVED_REPLY" if stale else x.review_state,
 "evidence_check_current":bool(x.evidence_checked and not stale),
 "review_action_required":_attention("RECHECK_SAVED_REPLY" if stale else x.review_state),
 "human_accuracy":None,"legal_signoff":False,"client_acceptance":False}

@router.get("")
def list_reviews(response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
 _gate(db,user)
 rows=db.query(SavedReplyReview).filter(SavedReplyReview.owner_id==user.id).order_by(SavedReplyReview.updated_at.desc()).limit(120).all()
 # Owned threads are fetched once for this request, with no global cache.
 ids=list({row.thread_id for row in rows})
 owned={row.id:row for row in (db.query(AssistantThread).filter(
  AssistantThread.user_id==user.id,AssistantThread.id.in_(ids)).all() if ids else [])}
 out=[]
 for r in rows:
  stamp=None
  thread=owned.get(r.thread_id)
  if thread is not None:
   try:
    messages=_read_messages(thread)
    scope=_reply_scope(messages,r.answer_message_index)
    if scope["eligible"]:
     pair=messages[r.answer_message_index-1:r.answer_message_index+1]
     stamp=hashlib.sha256(json.dumps(pair,sort_keys=True,
      ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
   except HTTPException:
    pass
  out.append(_output(r,stamp!=r.reply_fingerprint))
 counts=dict(sorted(Counter(x["effective_review_state"] for x in out).items()))
 action_counts=dict(sorted(Counter(x["review_action_required"] for x in out).items()))
 response.headers["Cache-Control"]="private, no-store"
 return {"schema":"BAWASLU_PERSISTENT_REPLY_REVIEWS_V1630","records":out,
 "review_progress_counts":counts,"review_count":len(out),
 "stale_review_count":counts.get("RECHECK_SAVED_REPLY",0),
 "completed_current_count":sum(counts.get(s,0) for s in COMPLETE),
 "review_action_counts":action_counts,
 "needs_attention_count":sum(v for k,v in action_counts.items()
  if k!="NO_FURTHER_ACTION_PROPOSED"),
 "last_owner_review_activity_at":rows[0].updated_at.isoformat() if rows else None,
 "counts_are_owned_operational_progress_only":True,
 "model_accuracy_measured":False,"formal_client_acceptance":False}

# Pilot inventory is a bounded, owner-scoped review queue, not an accuracy sample.
# Reuses saved history and current persisted review state, with no AI generation.
@router.get("/pilot-queue")
def pilot_queue(response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
 _gate(db,user)
 threads=db.query(AssistantThread).filter(
  AssistantThread.user_id==user.id).order_by(
  AssistantThread.updated_at.desc()).limit(40).all()
 all_reviews=db.query(SavedReplyReview).filter(
  SavedReplyReview.owner_id==user.id).limit(120).all()
 existing={(r.thread_id,r.answer_message_index):r for r in all_reviews}
 records=[]
 for thread in threads:
  try:messages=_read_messages(thread)
  except HTTPException:continue
  for index,msg in enumerate(messages):
   if not isinstance(msg,dict) or msg.get("role")!="assistant":continue
   scoped=_reply_scope(messages,index)
   old=existing.get((thread.id,index))
   changed=False
   if old:
    if not scoped["eligible"]:
     changed=True
    else:
     pair=messages[index-1:index+1]
     current=hashlib.sha256(json.dumps(pair,sort_keys=True,
       ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
     changed=current!=old.reply_fingerprint
   if old and changed:state="RECHECK_SAVED_REPLY"
   elif not scoped["eligible"]:state="INELIGIBLE_FOR_AUDIT"
   elif old:state=old.review_state
   else:state="NOT_STARTED"
   records.append({"thread_id":thread.id,"answer_message_index":index,
    "eligible":scoped["eligible"],"reason_code":scoped["reason_code"],
    "saved_source_count":len(scoped["source_ids"]),
    "displayed_citation_count":scoped["cited_count"],
    "cited_only_source_count":scoped.get("cited_only_source_count",0),
    "pilot_review_state":state,
    "review_version":old.version if old else 0,
    "reviewer_id":old.reviewer_id if old else None,
    "last_review_at":old.updated_at.isoformat() if old else None,
    "review_action_required":(
      "INSPECT_HISTORY_FORMAT_MANUALLY" if state=="INELIGIBLE_FOR_AUDIT"
      else "CONTINUE_REVIEW" if state=="NOT_STARTED" else _attention(state)),
    "evidence_checked_current":bool(old and old.evidence_checked and not changed
      and scoped["eligible"]),
    "source_permission_rechecked_at_listing":False})
   if len(records)>=120:break
  if len(records)>=120:break
 priority={"RECHECK_SAVED_REPLY":0,"EVIDENCE_CHECKED_FOLLOWUP_NEEDED":1,
  "REVIEW_BLOCKED":2,"EVIDENCE_CHECK_IN_PROGRESS":3,"PENDING_REVIEW":4,
  "NOT_STARTED":5,"INELIGIBLE_FOR_AUDIT":6,
  "EVIDENCE_CHECKED_NO_FURTHER_ACTION":7}
 # Stable ties preserve updated-thread order, not a claim about importance.
 records.sort(key=lambda x:priority.get(x["pilot_review_state"],6))
 counts=dict(sorted(Counter(x["pilot_review_state"] for x in records).items()))
 response.headers["Cache-Control"]="private, no-store"
 return {"schema":"BAWASLU_OWNED_SAVED_REPLY_PILOT_QUEUE_V1633",
  "candidates":records,"candidate_count":len(records),
  "eligible_count":sum(x["eligible"] for x in records),
  "pilot_state_counts":counts,
  "recommended_next_batch_count":min(5,sum(
   x["eligible"] and x["pilot_review_state"] not in
   {"EVIDENCE_CHECKED_NO_FURTHER_ACTION"} for x in records)),
  "inventory_is_bounded":True,"selection_is_not_representative":True,
  "source_permission_rechecked_at_listing":False,
  "human_accuracy":None,"legal_signoff":False,
  "formal_client_acceptance":False,"database_writes":0}

# Read-only handoff metadata. No answers, evidence text, or client decisions.
_HANDOFF_BUCKETS={
 "NOT_STARTED":"AWAITING_REVIEW",
 "PENDING_REVIEW":"AWAITING_REVIEW",
 "EVIDENCE_CHECK_IN_PROGRESS":"UNDER_REVIEW",
 "REVIEW_BLOCKED":"BLOCKED",
 "RECHECK_SAVED_REPLY":"STALE_RECHECK_REQUIRED",
 "INELIGIBLE_FOR_AUDIT":"INELIGIBLE",
 "EVIDENCE_CHECKED_FOLLOWUP_NEEDED":"FOLLOWUP_REQUIRED",
 "EVIDENCE_CHECKED_NO_FURTHER_ACTION":"EVIDENCE_CHECKED_NO_ACTION_PROPOSED",
}

@router.get("/pilot-handoff")
def pilot_handoff(response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
 snapshot=pilot_queue(Response(),user,db)
 records=[{
  "thread_id":item["thread_id"],
  "answer_message_index":item["answer_message_index"],
  "handoff_bucket":_HANDOFF_BUCKETS[item["pilot_review_state"]],
  "pilot_review_state":item["pilot_review_state"],
  "eligible":item["eligible"],
  "review_version":item["review_version"],
  "reviewer_id":item["reviewer_id"],
  "last_review_at":item["last_review_at"],
  "evidence_checked_current":item["evidence_checked_current"],
  "review_action_required":item["review_action_required"],
 } for item in snapshot["candidates"]]
 counts=dict(sorted(Counter(item["handoff_bucket"] for item in records).items()))
 followups=counts.get("FOLLOWUP_REQUIRED",0)
 blocked=counts.get("BLOCKED",0)+counts.get("STALE_RECHECK_REQUIRED",0)+counts.get("INELIGIBLE",0)
 response.headers["Cache-Control"]="private, no-store"
 return {
  "schema":"BAWASLU_OWNED_PILOT_HANDOFF_V1634",
  "owner_user_id":user.id,
  "scope":"CURRENT_USER_40_LATEST_THREADS_MAX_120_REPLIES",
  "inventory_count":len(records),
  "handoff_bucket_counts":counts,
  "followup_required_count":followups,
  "blocked_or_recheck_count":blocked,
  "evidence_checked_no_action_count":counts.get("EVIDENCE_CHECKED_NO_ACTION_PROPOSED",0),
  "rows":records,
  "bounded_inventory_not_all_historical_replies":True,
  "source_authorization_at_export":False,
  "answer_text_included":False,
  "source_excerpts_included":False,
  "human_accuracy":None,
  "legal_signoff":False,
  "formal_client_acceptance":False,
  "model_generation_verified":False,
  "database_writes":0,
 }

@router.post("")
def save_review(payload:ReviewSave,response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
 principal=_gate(db,user)
 if payload.review_state not in STATES:raise HTTPException(422,"Invalid review state")
 if payload.evidence_checked!=(payload.review_state in COMPLETE):
  raise HTTPException(422,"Evidence attestation must match reviewed outcome")
 pair,scope,fingerprint=_owned(db,user,payload.thread_id,payload.answer_message_index)
 route=_historical_review_route("AUDITED",_historical_citation_coverage(scope))
 if payload.review_state in COMPLETE:
  req=MixedAnswerAuditRequest(source_ids=scope["source_ids"],question=pair[0]["text"],answer=pair[1]["text"])
  fresh=resolve_mixed_audit_sources(db,principal,req)
  audited=build_mixed_answer_audit(fresh,req)
  route=_historical_review_route("AUDITED",_historical_citation_coverage(scope),audited["issue_triage"]["issue_candidate_count"])
 old=db.query(SavedReplyReview).filter(SavedReplyReview.owner_id==user.id,
  SavedReplyReview.thread_id==payload.thread_id,SavedReplyReview.answer_message_index==payload.answer_message_index).first()
 now=datetime.utcnow()
 if old is None:
  if payload.expected_version!=0:raise HTTPException(409,"Review changed; reload")
  row=SavedReplyReview(owner_id=user.id,thread_id=payload.thread_id,
   answer_message_index=payload.answer_message_index,reply_fingerprint=fingerprint,
   review_state=payload.review_state,evidence_checked=payload.evidence_checked,
   reviewer_id=user.id,review_route=route,version=1,created_at=now,updated_at=now)
  db.add(row)
  try:db.flush()
  except Exception:
   db.rollback()
   raise HTTPException(409,"Concurrent review; reload")
  db.add(SavedReplyReviewEvent(review_id=row.id,actor_id=user.id,from_state="NOT_RECORDED",
    to_state=payload.review_state,version=1,at=now))
 else:
  if old.version!=payload.expected_version or old.reply_fingerprint!=fingerprint:
   raise HTTPException(409,"Review version or saved reply changed; reload")
  previous_state=old.review_state
  changed=db.execute(update(SavedReplyReview).where(
   SavedReplyReview.id==old.id,SavedReplyReview.owner_id==user.id,
   SavedReplyReview.version==payload.expected_version,
   SavedReplyReview.reply_fingerprint==fingerprint).values(
    review_state=payload.review_state,evidence_checked=payload.evidence_checked,
    reviewer_id=user.id,review_route=route,version=payload.expected_version+1,updated_at=now),
    execution_options={"synchronize_session":False})
  if changed.rowcount!=1:
   db.rollback()
   raise HTTPException(409,"Concurrent review; reload")
  db.add(SavedReplyReviewEvent(review_id=old.id,actor_id=user.id,from_state=previous_state,
   to_state=payload.review_state,version=payload.expected_version+1,at=now))
 db.commit()
 result=db.query(SavedReplyReview).filter(SavedReplyReview.owner_id==user.id,
   SavedReplyReview.thread_id==payload.thread_id,
   SavedReplyReview.answer_message_index==payload.answer_message_index).one()
 response.headers["Cache-Control"]="private, no-store"
 return {"schema":"BAWASLU_PERSISTENT_REPLY_REVIEW_V1630","record":_output(result),
  "persisted":True,"legal_signoff":False,"client_acceptance":False}

@router.get("/{thread_id}/{index}/history")
def history(thread_id:str,index:int,response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
 _gate(db,user)
 r=db.query(SavedReplyReview).filter(SavedReplyReview.owner_id==user.id,
   SavedReplyReview.thread_id==thread_id,SavedReplyReview.answer_message_index==index).first()
 if r is None:raise HTTPException(404,"Review unavailable")
 # An owned review trail remains inspectable when the saved reply changed,
 # became ineligible, or was deleted. No historical answer text is returned.
 try:
  _,_,fingerprint=_owned(db,user,thread_id,index)
 except HTTPException:
  fingerprint=None
 recent=db.query(SavedReplyReviewEvent).filter(
  SavedReplyReviewEvent.review_id==r.id).order_by(
  SavedReplyReviewEvent.id.desc()).limit(50).all()
 events=list(reversed(recent))
 response.headers["Cache-Control"]="private, no-store"
 return {"record":_output(r,fingerprint!=r.reply_fingerprint),
  "events":[{"actor_user_id":e.actor_id,"from_state":e.from_state,
    "to_state":e.to_state,"version":e.version,"at":e.at.isoformat()} for e in events],
  "events_returned":len(events),"history_window":"MOST_RECENT_50",
  "history_truncated":r.version>len(events),"total_recorded_versions":r.version,
  "legal_signoff":False,"client_acceptance":False}
