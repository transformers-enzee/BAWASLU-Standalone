"""AI-5 durable, owner-private saved chats and frozen recipient-scoped shares.

All access uses SmartRadar's authenticated User and current AccessGrant. The
Supabase public tables have RLS enabled and no Data API permissions; only the
backend database connection can access this application-owned content.

Saved chats are explicit opt-in and snapshots are not new factual evidence.
Uploaded file bytes/text are NEVER stored here. Shared copies are strictly
PUBLIC research only; mixed, saved-record, or attachment evidence is blocked.
"""
import copy
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import User
from app.access import profile, has
from . import state

MAX_SAVED=40
MAX_MESSAGES=100
MAX_BYTES=1_800_000
MAX_RECIPIENTS=10
TITLE_LIMIT=160
EXPIRY_DAYS=(1,7,30)
UUID_RE=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TOKEN_RE=re.compile(r"^[a-zA-Z0-9_-]{35,120}$")


class AI5SavedChat(Base):
    __tablename__="ai5_saved_chats"
    __table_args__=(UniqueConstraint("owner_user_id","conversation_id",
                      name="uq_ai5_saved_owner_conversation"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    owner_user_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False,index=True)
    conversation_id:Mapped[str]=mapped_column(String(36),nullable=False)
    title:Mapped[str]=mapped_column(String(TITLE_LIMIT),nullable=False)
    turns_json:Mapped[str]=mapped_column(Text,nullable=False,default="[]")
    draft_revisions_json:Mapped[str]=mapped_column(Text,nullable=False,default="{}")
    scope_fingerprint:Mapped[str]=mapped_column(Text,nullable=False,default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=False)


class AI5SharedSnapshot(Base):
    __tablename__="ai5_shared_snapshots"
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    sender_user_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False,index=True)
    conversation_id:Mapped[str]=mapped_column(String(36),nullable=False)
    token_digest:Mapped[str]=mapped_column(String(64),unique=True,nullable=False,index=True)
    scope:Mapped[str]=mapped_column(String(18),nullable=False)
    snapshot_json:Mapped[str]=mapped_column(Text,nullable=False)
    recipient_user_ids_json:Mapped[str]=mapped_column(Text,nullable=False)
    expires_at:Mapped[datetime]=mapped_column(DateTime,nullable=False)
    revoked_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,nullable=False)


def _json(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",":"),default=str)


def _bounded(value):
    data=_json(value)
    if len(data.encode("utf-8"))>MAX_BYTES:
        raise HTTPException(413,"Saved chat exceeds the storage limit; start a new chat.")
    return data


def _validated_id(value):
    if not isinstance(value,str) or not UUID_RE.fullmatch(value.lower()):
        raise HTTPException(422,"Invalid conversation ID")
    return value.lower()


def _title(value,fallback="Saved AI-5 chat"):
    if not isinstance(value,str):
        raise HTTPException(422,"Invalid chat name")
    clean=re.sub(r"\s+"," ",value).strip()[:TITLE_LIMIT]
    return clean or fallback[:TITLE_LIMIT]


def _owned(db,user,chat_id):
    row=db.query(AI5SavedChat).filter(
        AI5SavedChat.id==chat_id,AI5SavedChat.owner_user_id==user.id).first()
    if not row:raise HTTPException(404,"Saved chat not found")
    return row


def _by_conversation(db,user,conversation_id):
    return db.query(AI5SavedChat).filter(
       AI5SavedChat.owner_user_id==user.id,
       AI5SavedChat.conversation_id==conversation_id).first()


def _requires_private_scope(turn):
    return (bool(turn.get("used_saved")) or
            str(turn.get("source_mode") or "")=="SMARTRADAR_ONLY" or
            any(str(x.get("type") or "").startswith(("SAVED_","ATTACHMENT_"))
                for x in turn.get("sources",[])))


def _assert_current_scope(row,grant):
    stored=json.loads(row.turns_json or "[]")
    if any(_requires_private_scope(t) for t in stored):
        if row.scope_fingerprint!=state.fingerprint(grant):
            raise HTTPException(403,"Your access changed. This saved chat contains restricted evidence; ask an administrator to review permissions.")
    return stored



def _durable_turn(source,conversation_id):
    """Persist answers/citations, not uploaded document text or file bytes."""
    t=copy.deepcopy(source)
    t["conversation_id"]=conversation_id
    for src in t.get("sources",[]):
        if str(src.get("type") or "").startswith("ATTACHMENT_"):
            for field in ("excerpt","text","sections","file_bytes","content"):
                src.pop(field,None)
    t.pop("attachment_content",None)
    return t


def _public_result(turn):
    """Rebuild the chat UI from trusted saved server turns, not client claims."""
    sources=[{k:s.get(k) for k in (
        "id","type","title","url","resolved_url","read_status","basis",
        "published_at","updated_at","consulted_at","section","reason",
        "reliability","duplicate_of","search_dimensions","document_type")}
        for s in turn.get("sources",[]) if isinstance(s,dict)]
    trace=copy.deepcopy(turn.get("research_trace") or {})
    trace["sources"]=sources
    trace.setdefault("public_status","RESTORED_SAVED_SNAPSHOT")
    trace.setdefault("searched_at",turn.get("searched_at"))
    trace.setdefault("retention","SAVED_APPLICATION_STORAGE")
    return {"assistant":"AI-5","turn_id":turn["turn_id"],
            "conversation_id":turn.get("conversation_id",""),
            "mode":turn.get("mode","GENERAL_RESEARCH"),
            "action_mode":turn.get("action_mode","OPERATIONAL"),
            "source_mode":turn.get("source_mode","WEB_ONLY"),
            "answer":copy.deepcopy(turn.get("answer") or {}),
            "research_trail":trace,
            "synthesis_status":"SAVED_SNAPSHOT",
            "actions_executed":False}


def _messages(turns,drafts):
    result=[]
    for t in turns:
        result.append({"role":"user","text":t.get("question","")})
        reply=_public_result(t)
        reply["conversation_id"]=t.get("conversation_id","")
        override=drafts.get(t.get("turn_id"))
        if isinstance(override,str) and reply["answer"].get("draft"):
            reply["answer"]["draft"]=override
        result.append({"role":"assistant","data":reply})
    return result


def _view(row,include=False,grant=None):
    obj={"id":row.id,"conversation_id":row.conversation_id,
         "title":row.title,"created_at":row.created_at.isoformat(),
         "updated_at":row.updated_at.isoformat()}
    if include:
        turns=_assert_current_scope(row,grant)
        drafts=json.loads(row.draft_revisions_json or "{}")
        obj["messages"]=_messages(turns,drafts)
        obj["message_count"]=len(turns)*2
        obj["attachments_note"]="Previously uploaded files are not retained. Reattach them before referencing or exporting attachment-backed answers."
    return obj


def list_saved(db,user,grant):
    rows=db.query(AI5SavedChat).filter(AI5SavedChat.owner_user_id==user.id).order_by(
        AI5SavedChat.updated_at.desc()).limit(MAX_SAVED).all()
    return {"saved_chats":[_view(r) for r in rows]}


def create_saved(db,user,grant,conversation_id,title,draft_revisions=None):
    cid=_validated_id(conversation_id)
    if _by_conversation(db,user,cid):
        raise HTTPException(409,"This conversation is already saved")
    n=db.query(func.count(AI5SavedChat.id)).filter(
        AI5SavedChat.owner_user_id==user.id).scalar() or 0
    if n>=MAX_SAVED:raise HTTPException(409,"Saved-chat limit reached. Delete an old chat.")
    turns=[_durable_turn(t,cid) for t in state.turns(user,cid,grant)]
    if not turns:raise HTTPException(409,"Ask AI-5 a question before saving a chat")
    revisions=_validate_drafts(turns,draft_revisions or {})
    row=AI5SavedChat(id=str(uuid.uuid4()),owner_user_id=user.id,
        conversation_id=cid,title=_title(title,str(turns[0].get("question") or "")[:TITLE_LIMIT]),
        turns_json=_bounded(turns),draft_revisions_json=_bounded(revisions),
        scope_fingerprint=state.fingerprint(grant))
    db.add(row);db.commit();db.refresh(row)
    return _view(row,True,grant)


def open_saved(db,user,grant,chat_id):
    row=_owned(db,user,chat_id)
    turns=_assert_current_scope(row,grant)
    # Replace expired/in-process state; never replay extracted attachment text.
    state.restore(user,row.conversation_id,grant,turns[-state.MAX_TURNS:])
    return _view(row,True,grant)


def rename_saved(db,user,chat_id,title):
    row=_owned(db,user,chat_id)
    row.title=_title(title);row.updated_at=datetime.utcnow()
    db.commit();return _view(row)


def delete_saved(db,user,chat_id):
    row=_owned(db,user,chat_id)
    # Deletion also revokes independent share copies for this conversation.
    db.query(AI5SharedSnapshot).filter(
       AI5SharedSnapshot.sender_user_id==user.id,
       AI5SharedSnapshot.conversation_id==row.conversation_id).update(
           {AI5SharedSnapshot.revoked_at:datetime.utcnow(),
            AI5SharedSnapshot.snapshot_json:"{}",
            AI5SharedSnapshot.recipient_user_ids_json:"[]"},
           synchronize_session=False)
    db.delete(row);db.commit()
    return {"ok":True,"shares_revoked":True}


def _validate_drafts(turns,payload):
    if not isinstance(payload,dict) or len(payload)>MAX_MESSAGES:
        raise HTTPException(422,"Invalid draft revisions")
    eligible={t["turn_id"] for t in turns if (t.get("answer") or {}).get("draft")}
    result={}
    for k,v in payload.items():
        if k not in eligible or not isinstance(v,str) or len(v)>16000:
            raise HTTPException(422,"Draft revision does not match an editable answer")
        result[k]=v
    return result


def save_draft(db,user,chat_id,turn_id,text):
    row=_owned(db,user,chat_id)
    turns=json.loads(row.turns_json or "[]")
    if turn_id not in {t.get("turn_id") for t in turns if (t.get("answer") or {}).get("draft")}:
        raise HTTPException(404,"Editable answer not found")
    if not isinstance(text,str) or len(text)>16000:
        raise HTTPException(422,"Draft must contain at most 16000 characters")
    data=json.loads(row.draft_revisions_json or "{}")
    data[turn_id]=text
    row.draft_revisions_json=_bounded(data);row.updated_at=datetime.utcnow()
    db.commit();return {"ok":True,"status":"Saved"}


def auto_append(db,user,grant,conversation_id,turn):
    """Server-side append is authoritative; never trust client-provided replies."""
    row=_by_conversation(db,user,conversation_id)
    if not row:return {"status":"NOT_SAVED"}
    prior=_assert_current_scope(row,grant)
    if len(prior)>=MAX_MESSAGES//2:
        return {"status":"COULD_NOT_SAVE","reason":"Saved conversation reached 50 answers"}
    record=_durable_turn(turn,conversation_id)
    prior.append(record)
    row.turns_json=_bounded(prior)
    row.updated_at=datetime.utcnow()
    db.commit()
    return {"status":"SAVED","saved_chat_id":row.id}



def sync_pending(db,user,grant,chat_id):
    """Explicit recovery when automatic persistence reported Couldn't save."""
    row=_owned(db,user,chat_id)
    prior=_assert_current_scope(row,grant)
    seen={t.get("turn_id") for t in prior}
    for t in state.turns(user,row.conversation_id,grant):
        if t.get("turn_id") not in seen:
            prior.append(_durable_turn(t,row.conversation_id))
            seen.add(t.get("turn_id"))
    if len(prior)>MAX_MESSAGES//2:
        raise HTTPException(409,"Saved chat is at the 50-answer limit")
    row.turns_json=_bounded(prior)
    row.updated_at=datetime.utcnow()
    db.commit()
    return {"status":"SAVED","saved_chat_id":row.id,"answer_count":len(prior)}

def _turns_for_share(db,user,grant,conversation_id):
    row=_by_conversation(db,user,conversation_id)
    if row:
        turns=copy.deepcopy(_assert_current_scope(row,grant))
        edits=json.loads(row.draft_revisions_json or "{}")
        for t in turns:
            if t.get("turn_id") in edits and (t.get("answer") or {}).get("draft"):
                t["answer"]["draft"]=edits[t["turn_id"]]
        return turns
    return state.turns(user,conversation_id,grant)


def _shareable(turn):
    if turn.get("source_mode")!="WEB_ONLY" or turn.get("used_saved") or turn.get("used_attachment"):
        return False,"Answer uses a non-public source mode or saved SmartRadar evidence"
    sources=turn.get("sources",[])
    if any(not str(s.get("type") or "").startswith("PUBLIC_") for s in sources):
        return False,"Answer contains uploaded or restricted sources"
    # No added content/attachment excerpts in public-only shared messages.
    return True,""


def _eligible_recipients(db,owner,emails):
    if not isinstance(emails,list) or not 1<=len(emails)<=MAX_RECIPIENTS:
        raise HTTPException(422,"Choose 1–10 colleagues")
    addresses=[]
    for value in emails:
        if not isinstance(value,str):raise HTTPException(422,"Invalid recipient email")
        addr=value.strip().lower()
        if not re.fullmatch(r"[^@\s]{1,100}@[^@\s]{1,140}",addr):
            raise HTTPException(422,"Invalid recipient email")
        if addr not in addresses:addresses.append(addr)
    rows=db.query(User).filter(func.lower(User.email).in_(addresses)).all()
    known={r.email.lower():r for r in rows}
    blocked=[];ids=[]
    for email in addresses:
        person=known.get(email)
        if not person or person.id==owner.id:
            blocked.append(email+" — colleague unavailable")
            continue
        grant=profile(db,person)
        if not has(grant,"view_intelligence"):
            blocked.append(email+" — no current SmartRadar intelligence access")
        else:ids.append(person.id)
    return ids,blocked,addresses


def _public_snapshot(turn,include_trail):
    allowed=[{k:s.get(k) for k in (
        "id","type","title","url","resolved_url","read_status","basis",
        "published_at","updated_at","reason","section","search_dimensions")}
        for s in turn.get("sources",[])
        if str(s.get("type") or "").startswith("PUBLIC_")]
    result={"turn_id":turn.get("turn_id"),"question":str(turn.get("question") or "")[:3200],
            "answer":copy.deepcopy(turn.get("answer") or {}),
            "mode":turn.get("mode"),"source_mode":"WEB_ONLY",
            "sources":allowed,"created_at":turn.get("created_at")}
    if include_trail:
        trace=copy.deepcopy(turn.get("research_trace") or {})
        trace.pop("model_passages",None)  # raw scraped passages not shareable by default
        trace["sources"]=allowed
        result["research_trail"]=trace
    return result


def share_preview(db,user,grant,conversation_id,scope,turn_id,emails,include_trail):
    cid=_validated_id(conversation_id)
    if scope not in ("ANSWER","CONVERSATION"):
        raise HTTPException(422,"Invalid share selection")
    if type(include_trail) is not bool:
        raise HTTPException(422,"Research Trail option must be true or false")
    turns=_turns_for_share(db,user,grant,cid)
    if not turns:raise HTTPException(404,"Conversation unavailable")
    if scope=="ANSWER":
        turns=[t for t in turns if t.get("turn_id")==turn_id]
        if not turns:raise HTTPException(404,"Answer unavailable")
    ids,blocked,addresses=_eligible_recipients(db,user,emails)
    selected=[];reasons=[]
    for t in turns:
        ok,reason=_shareable(t)
        if not ok:
            reasons.append({"turn_id":t.get("turn_id"),"question":t.get("question"),
                            "reason":reason})
        else:selected.append(_public_snapshot(t,include_trail))
    frozen={"title":"AI-5 shared answer" if scope=="ANSWER" else "AI-5 shared conversation",
            "scope":scope,"answers":selected,"include_research_trail":include_trail}
    digest=hashlib.sha256(_json({"preview":frozen,
              "recipients":addresses}).encode()).hexdigest()
    return {"can_share":bool(ids) and not blocked and not reasons and bool(selected),
            "blocked_recipients":blocked,"blocked_content":reasons,
            "recipients":addresses,"selected_count":len(selected),
            "preview":frozen,"preview_digest":digest}


def create_share(db,user,grant,body):
    scope=body.get("scope")
    preview=share_preview(db,user,grant,body.get("conversationId"),scope,
        body.get("turnId"),body.get("recipients"),body.get("includeResearchTrail",False))
    if not preview["can_share"]:
        raise HTTPException(409,{"message":"Selection cannot be shared. Narrow to public-only answers or change recipients.",
                                "blocked_content":preview["blocked_content"],
                                "blocked_recipients":preview["blocked_recipients"]})
    if body.get("previewDigest")!=preview["preview_digest"]:
        raise HTTPException(409,"Share preview is outdated. Preview again before publishing.")
    days=body.get("expiryDays",7)
    if type(days) is not int or days not in EXPIRY_DAYS:
        raise HTTPException(422,"Choose a 1-, 7- or 30-day expiry")
    cid=_validated_id(body.get("conversationId"))
    ids,_,addresses=_eligible_recipients(db,user,body.get("recipients"))
    token=str(uuid.uuid4())
    row=AI5SharedSnapshot(id=token,sender_user_id=user.id,
        conversation_id=cid,scope=scope,
        token_digest=hashlib.sha256(token.encode()).hexdigest(),
        snapshot_json=_bounded(preview["preview"]),
        recipient_user_ids_json=_json(ids),
        expires_at=datetime.utcnow()+timedelta(days=days))
    db.add(row);db.commit()
    return {"id":row.id,"token":token,"expires_at":row.expires_at.isoformat()+"Z",
            "scope":scope,"recipients":addresses}


def open_share(db,user,grant,token):
    if not isinstance(token,str) or not TOKEN_RE.fullmatch(token):
        raise HTTPException(404,"Shared copy unavailable")
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=db.query(AI5SharedSnapshot).filter(
        AI5SharedSnapshot.token_digest==digest).first()
    if not row or row.revoked_at is not None:
        raise HTTPException(404,"Shared copy unavailable or expired")
    if row.expires_at<=datetime.utcnow():
        row.snapshot_json="{}"
        row.recipient_user_ids_json="[]"
        db.commit()
        raise HTTPException(404,"Shared copy unavailable or expired")
    ids=json.loads(row.recipient_user_ids_json or "[]")
    if (user.id not in ids and user.id!=row.sender_user_id) or not has(grant,"view_intelligence"):
        raise HTTPException(403,"You are not authorised to open this shared copy")
    data=json.loads(row.snapshot_json)
    if any(any(not str(s.get("type","")).startswith("PUBLIC_")
               for s in t.get("sources",[])) for t in data.get("answers",[])):
        raise HTTPException(403,"Shared copy contains unavailable sources")
    return {"id":row.id,"expires_at":row.expires_at.isoformat()+"Z",
            "sender":"SmartRadar colleague","snapshot":data,"read_only":True}


def list_shares(db,user):
    # Expiry destroys shared content, leaving only link metadata for audit.
    db.query(AI5SharedSnapshot).filter(
        AI5SharedSnapshot.sender_user_id==user.id,
        AI5SharedSnapshot.expires_at<=datetime.utcnow(),
        AI5SharedSnapshot.snapshot_json!="{}").update(
        {AI5SharedSnapshot.snapshot_json:"{}",
         AI5SharedSnapshot.recipient_user_ids_json:"[]"},
        synchronize_session=False)
    db.commit()
    rows=db.query(AI5SharedSnapshot).filter(
        AI5SharedSnapshot.sender_user_id==user.id).order_by(
        AI5SharedSnapshot.created_at.desc()).limit(80).all()
    return {"shares":[{"id":r.id,"scope":r.scope,
              "conversation_id":r.conversation_id,"token":r.id,
              "created_at":r.created_at.isoformat()+"Z",
              "expires_at":r.expires_at.isoformat()+"Z",
              "revoked":bool(r.revoked_at),
              "expired":r.expires_at<=datetime.utcnow()}
              for r in rows]}


def revoke_share(db,user,share_id):
    row=db.query(AI5SharedSnapshot).filter(
        AI5SharedSnapshot.id==share_id,
        AI5SharedSnapshot.sender_user_id==user.id).first()
    if not row:raise HTTPException(404,"Share unavailable")
    row.revoked_at=datetime.utcnow()
    row.snapshot_json="{}"
    row.recipient_user_ids_json="[]"
    db.commit()
    return {"ok":True,"status":"REVOKED"}
