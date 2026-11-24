"""AI-5 owner-scoped, permission-bound conversation store.

Independent namespace on the existing short-lived, in-process attachment cache.
The conversation can switch modes without changing its identity. This is an
evaluation store, not durable or multi-worker safe; no history migration.
"""
import copy
import json
from fastapi import HTTPException
from app.ai4 import attachments as storage

MAX_TURNS=14
MAX_HISTORY_CHARS=18000


def owner(user):
    return "ai5:"+str(user.id)


def fingerprint(grant):
    return json.dumps({
        "role":grant.get("role"),"status":grant.get("status"),
        "geographic_scope":grant.get("geographic_scope"),
        "province":grant.get("province"),"province_code":grant.get("province_code"),
        "regency_city":grant.get("regency_city"),"regency_city_code":grant.get("regency_city_code"),
        "permissions":grant.get("permissions")
    },sort_keys=True,default=str)


def conversation(user,conversation_id,grant,create=False):
    key=owner(user)
    with storage.LOCK:
        record=storage.session(key,conversation_id,grant,create)
        if record is None:return None
        fp=fingerprint(grant)
        existing=record.get("ai5_scope")
        if existing and existing!=fp:
            storage.clear(key,conversation_id,grant)
            raise HTTPException(403,"Your permissions changed. Start a new AI-5 conversation.")
        record.setdefault("ai5_scope",fp)
        record.setdefault("ai5_turns",[])
        return record


def remove_conversation(user,conversation_id,grant):
    conversation(user,conversation_id,grant,False)
    return storage.clear(owner(user),conversation_id,grant)


def add_turn(user,conversation_id,grant,turn):
    with storage.LOCK:
        state=conversation(user,conversation_id,grant,True)
        state["ai5_turns"].append(copy.deepcopy(turn))
        state["ai5_turns"]=state["ai5_turns"][-MAX_TURNS:]
        return len(state["ai5_turns"])


def turns(user,conversation_id,grant):
    state=conversation(user,conversation_id,grant,False)
    return copy.deepcopy(state.get("ai5_turns",[])) if state else []


def get_turn(user,conversation_id,grant,turn_id):
    for t in reversed(turns(user,conversation_id,grant)):
        if t["turn_id"]==turn_id:return t
    raise HTTPException(404,"AI-5 answer was not found or has expired")


def attachments_for(user,conversation_id,grant):
    conversation(user,conversation_id,grant,False)
    return storage.evidence(owner(user),conversation_id,grant)


def add_file(user,conversation_id,grant,name,raw):
    conversation(user,conversation_id,grant,True)
    return storage.add_file(owner(user),conversation_id,grant,name,raw)


def add_link(user,conversation_id,grant,url):
    conversation(user,conversation_id,grant,True)
    return storage.add_link(owner(user),conversation_id,grant,url)


def attachment_list(user,conversation_id,grant):
    conversation(user,conversation_id,grant,False)
    return storage.list_items(owner(user),conversation_id,grant)


def remove_file(user,conversation_id,grant,aid):
    conversation(user,conversation_id,grant,False)
    return storage.remove(owner(user),conversation_id,grant,aid)


def filter_evidence(rows,source_mode,current_att_ids):
    """A Web-only answer cannot inherit earlier private SmartRadar evidence."""
    out=[]
    seen=set()
    for r in rows:
        if not isinstance(r,dict) or not r.get("id"):continue
        kind=str(r.get("type") or "")
        if source_mode=="WEB_ONLY" and (
            kind.startswith("SAVED_") or r.get("basis")=="FIXED_SAVED_SNAPSHOT"):
            continue
        if source_mode=="SMARTRADAR_ONLY" and kind.startswith("PUBLIC_"):
            continue
        if kind.startswith("ATTACHMENT_") and r["id"] not in current_att_ids:
            continue
        if r["id"] not in seen:
            seen.add(r["id"]);out.append(r)
    return out


def history_context(prior,source_mode,valid_attachment_ids):
    """Never launder old internal AI answers into Web-only synthesis."""
    summaries=[]
    remaining=MAX_HISTORY_CHARS
    for t in reversed(prior[-7:]):
        if source_mode=="WEB_ONLY" and t.get("used_saved"):
            continue
        if source_mode=="SMARTRADAR_ONLY" and t.get("used_public"):
            continue
        old_sources=filter_evidence(t.get("sources",[]),source_mode,valid_attachment_ids)
        if any(x.get("type","").startswith("ATTACHMENT_")
               and x["id"] not in valid_attachment_ids for x in t.get("sources",[])):
            # A removed file must not survive as an AI-written paraphrase.
            continue
        answer=t.get("answer") or {}
        excerpt=str(answer.get("body") or "")[:2500]
        detail={"question":str(t.get("question") or "")[:1000],
                "answer":excerpt,
                "draft":str(answer.get("draft") or "")[:2300],
                "mode":t.get("mode"),
                "source_ids":[r["id"] for r in old_sources][:12]}
        size=len(json.dumps(detail,ensure_ascii=False))
        if size>remaining:break
        remaining-=size
        summaries.append(detail)
    return list(reversed(summaries))


def latest_relevant(prior,source_mode,valid_attachment_ids):
    for t in reversed(prior):
        if source_mode=="WEB_ONLY" and t.get("used_saved"):continue
        if source_mode=="SMARTRADAR_ONLY" and t.get("used_public"):
            # A transform may use earlier original words, but cannot treat
            # public findings as SmartRadar-only sourced evidence.
            continue
        if any(x.get("type","").startswith("ATTACHMENT_")
               and x["id"] not in valid_attachment_ids for x in t.get("sources",[])):
            continue
        return t
    return None
