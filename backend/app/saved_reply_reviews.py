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

def _output(x,stale=False):
 return {"thread_id":x.thread_id,"answer_message_index":x.answer_message_index,
 "review_state":x.review_state,"evidence_checked":x.evidence_checked,
 "reviewer_id":x.reviewer_id,"review_route":x.review_route,
 "version":x.version,"updated_at":x.updated_at.isoformat(),"saved_reply_changed":stale,
 "effective_review_state":"RECHECK_SAVED_REPLY" if stale else x.review_state,
 "evidence_check_current":bool(x.evidence_checked and not stale),
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
 response.headers["Cache-Control"]="private, no-store"
 return {"schema":"BAWASLU_PERSISTENT_REPLY_REVIEWS_V1630","records":out,
 "review_progress_counts":counts,"review_count":len(out),
 "stale_review_count":counts.get("RECHECK_SAVED_REPLY",0),
 "completed_current_count":sum(counts.get(s,0) for s in COMPLETE),
 "counts_are_owned_operational_progress_only":True,
 "model_accuracy_measured":False,"formal_client_acceptance":False}

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
 _owned(db,user,thread_id,index)
 r=db.query(SavedReplyReview).filter(SavedReplyReview.owner_id==user.id,
   SavedReplyReview.thread_id==thread_id,SavedReplyReview.answer_message_index==index).first()
 if r is None:raise HTTPException(404,"Review unavailable")
 events=db.query(SavedReplyReviewEvent).filter(SavedReplyReviewEvent.review_id==r.id).order_by(SavedReplyReviewEvent.id).limit(100).all()
 response.headers["Cache-Control"]="private, no-store"
 _,_,fingerprint=_owned(db,user,thread_id,index)
 return {"record":_output(r,fingerprint!=r.reply_fingerprint),"events":[{"actor_user_id":e.actor_id,
   "from_state":e.from_state,"to_state":e.to_state,"version":e.version,
   "at":e.at.isoformat()} for e in events],"legal_signoff":False,"client_acceptance":False}
