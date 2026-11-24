"""AI-4 conversation-scoped attachments.

Untrusted file bytes are parsed in memory, never executed or inserted into
SmartRadar's global knowledge database. Cache is process-local, short-lived:
an intentional pilot limitation documented in the UI and review brief.
"""
import io
import os
import re
import threading
import time
import uuid
import zipfile
from pathlib import PurePath
from fastapi import HTTPException
from app.unified_ai.web import safe_url,read_page

TTL=60*60*12
MAX_BYTES=5*1024*1024
MAX_SECTIONS=45
MAX_TEXT=24000
MAX_ALL=75000
MAX_ATTACHMENTS=8
STORES={}
LOCK=threading.RLock()
VALID_ID=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
FORMAT={".pdf":b"%PDF-", ".docx":b"PK\x03\x04", ".txt":None}


def scope(profile):
    return tuple(str(profile.get(k) or "") for k in
                 ("geographic_scope","province_code","regency_city_code","status"))


def _key(user_id,conversation_id):
    if not isinstance(conversation_id,str) or not VALID_ID.fullmatch(conversation_id.lower()):
        raise HTTPException(422,"Invalid AI-4 conversation identifier")
    return str(user_id),conversation_id.lower()


def _purge():
    now=time.monotonic()
    for k,v in list(STORES.items()):
        if now-v["touched"]>TTL:STORES.pop(k,None)
    if len(STORES)>150:
        for k,_ in sorted(STORES.items(),key=lambda kv:kv[1]["touched"])[:len(STORES)-150]:
            STORES.pop(k,None)


def session(user_id,conversation_id,grant,create=False):
    key=_key(user_id,conversation_id)
    with LOCK:
        _purge()
        state=STORES.get(key)
        if state is None:
            if not create:return None
            state={"attachments":{},"mode":None,"scope":scope(grant),"touched":time.monotonic()}
            STORES[key]=state
        if state["scope"]!=scope(grant):
            STORES.pop(key,None)
            raise HTTPException(403,"Officer permission scope changed. Start a new AI-4 conversation.")
        state["touched"]=time.monotonic()
        return state


def bind_mode(user_id,conversation_id,grant,mode):
    with LOCK:
        state=session(user_id,conversation_id,grant,True)
        if state["mode"] is None:state["mode"]=mode
        if state["mode"]!=mode:
            raise HTTPException(409,"Source mode changed. Start a new conversation before changing source access.")
        return state


def file_sections(name,raw):
    name=PurePath(name or "").name[:160]
    suffix=os.path.splitext(name.lower())[1]
    if suffix not in FORMAT:raise HTTPException(422,"Only PDF, DOCX and UTF-8 TXT are supported")
    if not raw or len(raw)>MAX_BYTES:raise HTTPException(422,"File must be nonempty and at most 5 MB")
    signature=FORMAT[suffix]
    if signature and not raw.startswith(signature):
        raise HTTPException(422,"File content does not match its extension")
    parts=[]
    if suffix==".pdf":
        from pypdf import PdfReader
        try:
            reader=PdfReader(io.BytesIO(raw),strict=False)
            if reader.is_encrypted:raise HTTPException(422,"Unlock encrypted PDF before upload")
            if len(reader.pages)>MAX_SECTIONS:
                raise HTTPException(422,"PDF exceeds 45-page limit")
            for idx,page in enumerate(reader.pages,1):
                value=(page.extract_text() or "").strip()
                if value:parts.append((f"page {idx}",value))
        except HTTPException:raise
        except Exception as e:raise HTTPException(422,"PDF cannot be safely read") from e
    elif suffix==".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                info=z.infolist()
                if (len(info)>220 or sum(x.file_size for x in info)>18*1024*1024 or
                    any("vbaProject" in x.filename or x.filename.endswith((".exe",".dll",".js")) for x in info)):
                    raise HTTPException(422,"Unsafe or over-complex DOCX contents")
            from docx import Document
            doc=Document(io.BytesIO(raw))
            for idx,p in enumerate(doc.paragraphs,1):
                if p.text.strip():parts.append((f"paragraph {idx}",p.text.strip()))
            for ti,t in enumerate(doc.tables,1):
                for ri,row in enumerate(t.rows,1):
                    value=" | ".join(c.text.strip() for c in row.cells)
                    if value.strip(" |"):parts.append((f"table {ti} row {ri}",value))
        except HTTPException:raise
        except (zipfile.BadZipFile,ValueError,TypeError,KeyError,IndexError,OSError) as e:
            raise HTTPException(422,"DOCX cannot be safely read") from e
    else:
        if b"\x00" in raw:raise HTTPException(422,"Binary TXT is not supported")
        try:decoded=raw.decode("utf-8-sig")
        except UnicodeDecodeError as e:raise HTTPException(422,"TXT must use UTF-8") from e
        parts=[(f"section {i}",x.strip()) for i,x in
               enumerate(re.split(r"\n\s*\n",decoded),1) if x.strip()]
    if not parts:raise HTTPException(422,"No extractable text. Scanned documents need OCR before upload.")
    total=0;sections=[]
    for label,value in parts[:MAX_SECTIONS]:
        if total>=MAX_TEXT:break
        text=value[:min(2800,MAX_TEXT-total)]
        if text:sections.append({"section":label,"text":text});total+=len(text)
    return name,sections,(len(parts)>len(sections) or any(len(t)>2800 for _,t in parts[:MAX_SECTIONS]))


def _view(a):
    return {k:a[k] for k in ("id","title","kind","status","url","sections_count","truncated","source_basis")}


def _insert(state,record):
    with LOCK:
        rows=state["attachments"]
        if len(rows)>=MAX_ATTACHMENTS:
            raise HTTPException(422,"Maximum eight attachments per AI-4 conversation")
        total=sum(sum(len(x["excerpt"]) for x in a["sources"]) for a in rows.values())
        extra=sum(len(x["excerpt"]) for x in record["sources"])
        if total+extra>MAX_ALL:
            raise HTTPException(422,"Conversation attachment text limit reached")
        rows[record["id"]]=record
        return _view(record)


def add_file(user_id,conversation_id,grant,name,raw):
    name,sections,truncated=file_sections(name,raw)
    state=session(user_id,conversation_id,grant,True)
    aid=uuid.uuid4().hex
    ext=os.path.splitext(name.lower())[1]
    typ={".pdf":"ATTACHMENT_PDF",".docx":"ATTACHMENT_DOCX",".txt":"ATTACHMENT_TXT"}[ext]
    entries=[{"id":f"FILE-{aid[:12].upper()}-{i}","type":typ,
              "title":f"{name} · {part['section']}","url":"",
              "published_at":"","updated_at":"","read_status":"READ",
              "basis":"OFFICER_UPLOADED_UNVERIFIED",
              "excerpt":part["text"],"duplicate_of":"","location_verified":False,
              "reason":"Officer-supplied document section; not independently authenticated",
              "section":part["section"]} for i,part in enumerate(sections,1)]
    return _insert(state,{"id":aid,"title":name,"kind":"DOCUMENT","status":"READY",
                          "url":"","sections_count":len(entries),"truncated":truncated,
                          "source_basis":"OFFICER_UPLOADED_UNVERIFIED","sources":entries})


def add_link(user_id,conversation_id,grant,url):
    if not safe_url(url):raise HTTPException(422,"Only publicly reachable HTTPS URLs are supported")
    page=read_page({"url":url,"title":"","snippet":""})
    if page.get("read_status")!="READ":
        raise HTTPException(422,"Public link could not be opened and read ("+
                            str(page.get("reason") or "unavailable")[:110]+")")
    state=session(user_id,conversation_id,grant,True)
    aid=uuid.uuid4().hex
    entry={"id":f"LINK-{aid[:12].upper()}","type":"ATTACHMENT_PUBLIC_LINK",
           "title":page.get("title") or url,"url":page.get("resolved_url") or url,
           "published_at":page.get("published_at") or "",
           "updated_at":page.get("updated_at") or "",
           "read_status":"READ","basis":"OFFICER_ATTACHED_LIVE_PUBLIC_PAGE",
           "excerpt":str(page.get("excerpt") or "")[:MAX_TEXT],"duplicate_of":"",
           "location_verified":False,"reason":"Public page opened when link was added",
           "section":"retrieved public page"}
    return _insert(state,{"id":aid,"title":entry["title"],"kind":"LINK","status":"READY",
                          "url":entry["url"],"sections_count":1,"truncated":len(page.get("excerpt") or "")>MAX_TEXT,
                          "source_basis":"OFFICER_ATTACHED_LIVE_PUBLIC_PAGE","sources":[entry]})


def list_items(user_id,conversation_id,grant):
    state=session(user_id,conversation_id,grant,False)
    return [_view(x) for x in state["attachments"].values()] if state else []


def evidence(user_id,conversation_id,grant):
    state=session(user_id,conversation_id,grant,False)
    if state is None:return []
    return [dict(s) for a in state["attachments"].values() for s in a["sources"]]


def remove(user_id,conversation_id,grant,attachment_id):
    state=session(user_id,conversation_id,grant,False)
    if not state or attachment_id not in state["attachments"]:
        raise HTTPException(404,"Attachment not found in this conversation")
    with LOCK:state["attachments"].pop(attachment_id,None)
    return {"removed":True,"attachment_id":attachment_id}


def clear(user_id,conversation_id,grant):
    state=session(user_id,conversation_id,grant,False)
    if state:
        with LOCK:STORES.pop(_key(user_id,conversation_id),None)
    return {"cleared":True}
