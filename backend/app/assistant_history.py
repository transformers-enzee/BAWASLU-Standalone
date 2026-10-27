"""Authenticated, per-user conversation history for the Intelligence Assistant.

History is not evidence and does not trigger OpenAI calls. All reads/writes are
scoped to the currently authenticated user and require view_intelligence.
"""
from datetime import datetime
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from .db import Base, get_db
from .models import User
from .auth import current_user
from .access import profile, has

router = APIRouter(prefix="/api/assistant-history", tags=["assistant-history"])

class AssistantThread(Base):
    __tablename__ = "assistant_threads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), default="New conversation")
    messages_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ThreadPayload(BaseModel):
    id: str | None = None
    title: str = Field(default="New conversation", max_length=160)
    messages: list[dict] = Field(default_factory=list)

def require_access(db: Session, user: User):
    grant = profile(db, user)
    if grant.get("status") != "Active" or not has(grant, "view_intelligence"):
        raise HTTPException(status_code=403, detail="Intelligence access required")

def item_view(row, include_messages=False):
    value = {
        "id": row.id, "title": row.title,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat()
    }
    if include_messages:
        value["messages"] = json.loads(row.messages_json or "[]")
    return value

def clean_messages(messages):
    if len(messages) > 60:
        raise HTTPException(422, "Maximum 60 messages per conversation")
    clean = []
    for item in messages:
        if not isinstance(item, dict) or item.get("role") not in ("user", "assistant"):
            raise HTTPException(422, "Invalid conversation message")
        text = item.get("text", "")
        if not isinstance(text, str) or len(text) > 15000:
            raise HTTPException(422, "Invalid message text")
        records = item.get("records", [])
        if not isinstance(records, list):
            raise HTTPException(422, "Invalid supporting records")
        # Retain only the authorised evidence returned by the assistant endpoint
        # in a bounded display snapshot. Source records must be re-opened in Inbox.
        clean.append({
            "role": item["role"], "text": text,
            "records": [r for r in records[:12] if isinstance(r, dict)],
            "provider": item.get("provider") if isinstance(item.get("provider"), dict) else None,
            "grounding": item.get("grounding") if isinstance(item.get("grounding"), dict) else None,
        })
    if len(json.dumps(clean, ensure_ascii=False)) > 150000:
        raise HTTPException(422, "Conversation exceeds storage limit")
    return clean

@router.get("")
def list_threads(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_access(db, user)
    rows = db.query(AssistantThread).filter(AssistantThread.user_id == user.id).order_by(
        AssistantThread.updated_at.desc()).limit(40).all()
    return {"threads": [item_view(row) for row in rows]}

@router.get("/{thread_id}")
def get_thread(thread_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_access(db, user)
    row = db.query(AssistantThread).filter(AssistantThread.id == thread_id,
                                           AssistantThread.user_id == user.id).first()
    if not row:
        raise HTTPException(404, "Conversation unavailable")
    return item_view(row, True)

@router.put("")
def save_thread(body: ThreadPayload, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_access(db, user)
    messages = clean_messages(body.messages)
    title = body.title.strip()[:160] or "New conversation"
    if body.id and len(body.id) > 36:
        raise HTTPException(422, "Invalid conversation ID")
    row = None
    if body.id:
        row = db.query(AssistantThread).filter(AssistantThread.id == body.id,
                                               AssistantThread.user_id == user.id).first()
        if not row:
            raise HTTPException(404, "Conversation unavailable")
    if row is None:
        owned = db.query(func.count(AssistantThread.id)).filter(AssistantThread.user_id == user.id).scalar() or 0
        if owned >= 40:
            raise HTTPException(409, "Conversation limit reached; delete an old conversation")
        row = AssistantThread(id=str(uuid.uuid4()), user_id=user.id)
        db.add(row)
    row.title, row.messages_json = title, json.dumps(messages, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    db.commit()
    return item_view(row, True)

@router.delete("/{thread_id}")
def delete_thread(thread_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_access(db, user)
    row = db.query(AssistantThread).filter(AssistantThread.id == thread_id,
                                           AssistantThread.user_id == user.id).first()
    if not row:
        raise HTTPException(404, "Conversation unavailable")
    db.delete(row)
    db.commit()
    return {"ok": True}
