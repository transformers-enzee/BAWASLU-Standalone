"""Per-answer feedback for authorized SmartRadar conversations, no AI calls."""
import hashlib,json,uuid
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column,Session
from .db import Base,get_db
from .models import User
from .auth import current_user
from .assistant_history import AssistantThread,require_access

router=APIRouter(prefix="/api/assistant-feedback",tags=["assistant-feedback"])


class AssistantResponseFeedback(Base):
    __tablename__="assistant_response_feedback"
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    thread_id:Mapped[str]=mapped_column(String(36),ForeignKey("assistant_threads.id"),index=True,nullable=False)
    user_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False)
    message_index:Mapped[int]=mapped_column(Integer,nullable=False)
    rating:Mapped[str]=mapped_column(String(20),nullable=False)
    note:Mapped[str]=mapped_column(Text,default="")
    answer_sha256:Mapped[str]=mapped_column(String(64),nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class FeedbackIn(BaseModel):
    thread_id:str
    message_index:int=Field(ge=0,le=59)
    rating:str
    note:str=Field(default="",max_length=600)


@router.post("")
def upsert_feedback(body:FeedbackIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    require_access(db,user)
    if body.rating not in ("HELPFUL","NEEDS_IMPROVEMENT"):
        raise HTTPException(422,"Choose Helpful or Needs improvement")
    try:tid=str(uuid.UUID(body.thread_id))
    except ValueError:raise HTTPException(422,"Invalid conversation identifier")
    thread=db.query(AssistantThread).filter_by(id=tid,user_id=user.id).first()
    if not thread:raise HTTPException(404,"Conversation unavailable")
    messages=json.loads(thread.messages_json or "[]")
    if body.message_index>=len(messages) or messages[body.message_index].get("role")!="assistant":
        raise HTTPException(422,"Only a saved assistant reply can be reviewed")
    text=str(messages[body.message_index].get("text") or "")
    if not text:raise HTTPException(422,"Reply not available for feedback")
    fp=hashlib.sha256(text.encode()).hexdigest()
    row=db.query(AssistantResponseFeedback).filter_by(
        thread_id=tid,user_id=user.id,message_index=body.message_index).one_or_none()
    if not row:
        row=AssistantResponseFeedback(id=str(uuid.uuid4()),thread_id=tid,
              user_id=user.id,message_index=body.message_index)
        db.add(row)
    row.rating=body.rating;row.note=body.note.strip();row.answer_sha256=fp
    row.updated_at=datetime.utcnow();db.commit()
    return {"saved":True,"rating":row.rating,"message_index":row.message_index,"sent":False}
