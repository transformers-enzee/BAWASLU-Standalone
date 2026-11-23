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
            "attachment_ids":[str(x) for x in (item.get("attachment_ids") or [])[:8]
                 if isinstance(x,str) and len(x)==36] if isinstance(item.get("attachment_ids"),list) else [],
            "attached_source_ids":[str(x)[:100] for x in (item.get("attached_source_ids") or [])[:45]
                 if isinstance(x,str) and x.startswith("ATT-")] if isinstance(item.get("attached_source_ids"),list) else [],
            "assistant_mode":item.get("assistant_mode") if item.get("assistant_mode") in ("MANAGEMENT","OPERATIONAL") else "",
            "perspective":item.get("perspective") if item.get("perspective") in ("AUTO","EXECUTIVE","OPERATIONAL","RESEARCH") else "",
            "records": [r for r in records[:12] if isinstance(r, dict)],
            "provider": item.get("provider") if isinstance(item.get("provider"), dict) else None,
            "grounding": item.get("grounding") if isinstance(item.get("grounding"), dict) else None,
            "evidence_snapshot": item.get("evidence_snapshot") if isinstance(item.get("evidence_snapshot"),dict) else None,
            "response_profile": (str(item.get("response_profile") or "")[:24]
              if str(item.get("response_profile") or "") in
              ("PDF_GUIDANCE","SOCIAL_ANALYSIS","CASE_REVIEW","CROSS_MODULE_REVIEW","ACTION_REQUEST","GENERAL")
              else ""),
            "answer_language": str(item.get("answer_language") or "")[:12],
            "detected_tags": [t for t in (item.get("detected_tags") or [])[:18] if isinstance(t,dict)] if isinstance(item.get("detected_tags"),list) else [],
            "presentation_labels": {str(k)[:50]:str(v)[:120] for k,v in list((item.get("presentation_labels") or {}).items())[:70]} if isinstance(item.get("presentation_labels"),dict) else {},

            "workflow_mode":item.get("workflow_mode") if item.get("workflow_mode") in ("RESEARCH","STRATEGY_DRAFTING") else "",
            "source_consultation":[{
                "key":str(x.get("key") or "")[:32],
                "label":str(x.get("label") or "")[:80],
                "status":str(x.get("status") or "")[:40],
                "basis":str(x.get("basis") or "")[:55],
                "selected_count":int(x.get("selected_count") or 0) if str(x.get("selected_count") or "0").isdigit() else 0,
                "warning":str(x.get("warning") or "")[:220],
                "cited_source_ids":[str(y)[:50] for y in (x.get("cited_source_ids") or [])[:12] if isinstance(y,str)] if isinstance(x.get("cited_source_ids"),list) else [],
                "urls":[str(y)[:900] for y in (x.get("urls") or [])[:6] if isinstance(y,str) and y.startswith("https://")] if isinstance(x.get("urls"),list) else [],
            } for x in (item.get("source_consultation") or [])[:4] if isinstance(x,dict)] if isinstance(item.get("source_consultation"),list) else [],
            "structured_findings":[{
                "text":str(x.get("text") or "")[:900],
                "source_ids":[str(y)[:50] for y in (x.get("source_ids") or [])[:4] if isinstance(y,str)] if isinstance(x.get("source_ids"),list) else [],
                "evidence_class":str(x.get("evidence_class") or "")[:70],
                "support_status":str(x.get("support_status") or "")[:70],
            } for x in (item.get("structured_findings") or [])[:5] if isinstance(x,dict)] if isinstance(item.get("structured_findings"),list) else [],
            "decision_plan":[{
                "owner_role":str(x.get("owner_role") or "")[:200],
                "milestone":str(x.get("milestone") or "")[:500],
                "expected_output":str(x.get("expected_output") or "")[:300],
                "review_point":str(x.get("review_point") or "")[:400],
                "source_ids":[str(y)[:50] for y in (x.get("source_ids") or [])[:4] if isinstance(y,str)] if isinstance(x.get("source_ids"),list) else [],
            } for x in (item.get("decision_plan") or [])[:4] if isinstance(x,dict)] if isinstance(item.get("decision_plan"),list) else [],
            "draft_policy":"DRAFT_ONLY_STAFF_REVIEW_AND_SEND" if item.get("draft_policy")=="DRAFT_ONLY_STAFF_REVIEW_AND_SEND" else "",
            "analytical_findings": item.get("analytical_findings") if isinstance(item.get("analytical_findings"),dict) else None,
            "featured_sources": [x for x in item.get("featured_sources",[])[:6] if isinstance(x,dict)] if isinstance(item.get("featured_sources"),list) else [],
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
