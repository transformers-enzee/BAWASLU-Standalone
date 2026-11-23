"""Private per-thread assistant attachments; never entered into shared casework.

Requires the explicit assistant_chat_attachments migration. Plain extractable text
only is stored; original files are discarded after malware scanning and parsing.
A scan service must be configured (fail-closed) for uploaded documents.
"""
import hashlib, io, json, os, re, socket, struct, uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, Session
from .db import Base, get_db
from .auth import current_user
from .models import User
from .access import profile, has
from .assistant_history import AssistantThread

router=APIRouter(prefix="/api/assistant-attachments",tags=["assistant-attachments"])
MAX_BYTES=5*1024*1024
MAX_TEXT=24000
MAX_ATTACHMENTS=8
MAX_TOTAL_TEXT=80000
PERMITTED={".pdf",".docx",".txt"}
CITATION=re.compile(r"\[ATT-[a-f0-9]{32}-S\d+\]")
SCOPE_FIELDS=("geographic_scope","province_code","regency_city_code")


class AssistantChatAttachment(Base):
    __tablename__="assistant_chat_attachments"
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    thread_id:Mapped[str]=mapped_column(String(36),ForeignKey("assistant_threads.id"),index=True,nullable=False)
    user_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),index=True,nullable=False)
    kind:Mapped[str]=mapped_column(String(10),nullable=False)
    title:Mapped[str]=mapped_column(String(260),nullable=False)
    url:Mapped[str]=mapped_column(String(1900),default="")
    source_digest:Mapped[str]=mapped_column(String(64),nullable=False)
    status:Mapped[str]=mapped_column(String(32),default="READY")
    extracted_text:Mapped[str]=mapped_column(Text,nullable=False)
    sections_json:Mapped[str]=mapped_column(Text,default="[]")
    access_scope_json:Mapped[str]=mapped_column(Text,nullable=False)
    retrieved_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class LinkRequest(BaseModel):
    thread_id:str
    url:str


def _user_scope(db,user):
    p=profile(db,user)
    if not has(p,"view_intelligence"):
        raise HTTPException(403,"Assistant intelligence access required")
    return p


def _thread(db,user,thread_id):
    try:tid=str(uuid.UUID(str(thread_id)))
    except (ValueError,TypeError):raise HTTPException(422,"Invalid conversation identifier")
    row=db.query(AssistantThread).filter_by(id=tid,user_id=user.id).first()
    if row is None:raise HTTPException(404,"Conversation unavailable")
    return row


def _scope(p):return {key:str(p.get(key) or "") for key in SCOPE_FIELDS}


def _check_scope(row,p):
    try:original=json.loads(row.access_scope_json)
    except (ValueError,TypeError):raise HTTPException(403,"Attachment access scope invalid")
    if original!=_scope(p):
        raise HTTPException(403,"Attachment jurisdiction changed; reattach under current permissions")


def _limit(db,thread_id,extra=0):
    rows=db.query(AssistantChatAttachment).filter_by(thread_id=thread_id).all()
    if len(rows)>=MAX_ATTACHMENTS:raise HTTPException(422,"Maximum eight attachments per conversation")
    if sum(len(x.extracted_text or "") for x in rows)+extra>MAX_TOTAL_TEXT:
        raise HTTPException(422,"Conversation attachment text limit exceeded")


def _clamav_scan(data):
    host=os.getenv("ASSISTANT_CLAMAV_HOST","").strip()
    if not host:
        raise HTTPException(503,"Upload scanner is unavailable. Configure approved malware scanning; use Add link or paste a safe excerpt instead")
    port=int(os.getenv("ASSISTANT_CLAMAV_PORT","3310"))
    try:
        with socket.create_connection((host,port),timeout=7) as sock:
            sock.settimeout(10)
            sock.sendall(b"zINSTREAM\0")
            for i in range(0,len(data),65536):
                chunk=data[i:i+65536]
                sock.sendall(struct.pack(">I",len(chunk))+chunk)
            sock.sendall(struct.pack(">I",0))
            verdict=sock.recv(2048)
    except (OSError,ValueError) as exc:
        raise HTTPException(503,"Approved malware scanner did not complete; upload rejected") from exc
    if b"FOUND" in verdict:raise HTTPException(422,"Security scan rejected the uploaded file")
    if b"OK" not in verdict:raise HTTPException(503,"Malware scan inconclusive; upload rejected")


def _decode_document(name,data):
    ext=os.path.splitext(name.lower())[1]
    if ext not in PERMITTED:raise HTTPException(422,"Only PDF, DOCX and TXT files are supported")
    parts=[]
    if ext==".pdf":
        if not data.startswith(b"%PDF-"):raise HTTPException(422,"PDF signature invalid")
        from pypdf import PdfReader
        try:
            pdf=PdfReader(io.BytesIO(data),strict=False)
            if pdf.is_encrypted:raise HTTPException(422,"Encrypted PDF: unlock before attaching")
            if len(pdf.pages)>45:raise HTTPException(422,"PDF exceeds 45-page limit")
            for i,page in enumerate(pdf.pages,1):
                value=(page.extract_text() or "").strip()
                if value:parts.append((f"Page {i}",value))
        except HTTPException:raise
        except Exception as exc:raise HTTPException(422,"Unreadable PDF") from exc
    elif ext==".docx":
        if not data.startswith(b"PK\x03\x04"):raise HTTPException(422,"DOCX signature invalid")
        from docx import Document
        try:
            doc=Document(io.BytesIO(data))
            for i,paragraph in enumerate(doc.paragraphs,1):
                if paragraph.text.strip():parts.append((f"Paragraph {i}",paragraph.text.strip()))
            for ti,table in enumerate(doc.tables,1):
                for ri,row in enumerate(table.rows,1):
                    value=" | ".join(cell.text.strip() for cell in row.cells)
                    if value.strip(" |"):parts.append((f"Table {ti}, row {ri}",value))
        except Exception as exc:raise HTTPException(422,"Unreadable or encrypted DOCX") from exc
    else:
        try:value=data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:raise HTTPException(422,"TXT must be UTF-8 encoded") from exc
        parts=[(f"Section {i}",x.strip()) for i,x in enumerate(re.split(r"\n\s*\n",value),1) if x.strip()]
    if not parts:raise HTTPException(422,"No selectable text. Scanned pages require OCR before attaching")
    stored=[];total=0
    for label,part in parts:
        if total>=MAX_TEXT:break
        take=part[:min(3000,MAX_TEXT-total)]
        if take:stored.append({"section":label,"text":take});total+=len(take)
    return stored


def _store(db,user,p,thread,kind,title,url,sections,digest):
    content="\n".join(x["section"]+": "+x["text"] for x in sections)
    _limit(db,thread.id,len(content))
    row=AssistantChatAttachment(id=str(uuid.uuid4()),thread_id=thread.id,user_id=user.id,
         kind=kind,title=title[:260],url=url[:1900],source_digest=digest,
         extracted_text=content[:MAX_TEXT+1000],sections_json=json.dumps(sections,ensure_ascii=False),
         access_scope_json=json.dumps(_scope(p),sort_keys=True))
    db.add(row);db.commit()
    return _view(row)


def _view(row):
    return {"id":row.id,"thread_id":row.thread_id,"kind":row.kind,"title":row.title,
            "url":row.url,"status":row.status,
            "retrieved_at":row.retrieved_at.isoformat() if row.retrieved_at else "",
            "sections":len(json.loads(row.sections_json or "[]")),
            "chars":len(row.extracted_text or ""),"source_basis":"USER_SUPPLIED_UNVERIFIED"}


@router.post("/session")
def session(user:User=Depends(current_user),db:Session=Depends(get_db)):
    _user_scope(db,user)
    count=db.query(func.count(AssistantThread.id)).filter_by(user_id=user.id).scalar() or 0
    if count>=40:raise HTTPException(409,"Conversation limit reached")
    row=AssistantThread(id=str(uuid.uuid4()),user_id=user.id,title="New conversation")
    db.add(row);db.commit()
    return {"thread_id":row.id}


@router.get("/{thread_id}")
def list_attachments(thread_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=_user_scope(db,user);thread=_thread(db,user,thread_id)
    rows=db.query(AssistantChatAttachment).filter_by(thread_id=thread.id,user_id=user.id).all()
    for row in rows:_check_scope(row,p)
    return {"attachments":[_view(row) for row in rows]}


@router.post("/upload")
async def upload(thread_id:str=Form(...),file:UploadFile=File(...),
                 user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=_user_scope(db,user);thread=_thread(db,user,thread_id)
    name=os.path.basename(file.filename or "")[:200]
    if os.path.splitext(name.lower())[1] not in PERMITTED:
        raise HTTPException(422,"Unsupported file. Use PDF, DOCX or UTF-8 TXT")
    data=await file.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise HTTPException(422,"Maximum attachment size is 5 MB")
    if not data:raise HTTPException(422,"Empty document")
    _limit(db,thread.id)
    _clamav_scan(data)
    sections=_decode_document(name,data)
    return _store(db,user,p,thread,"DOCUMENT",name,"",sections,hashlib.sha256(data).hexdigest())


@router.post("/link")
def attach_link(body:LinkRequest,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=_user_scope(db,user);thread=_thread(db,user,body.thread_id)
    url=body.url.strip()
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422,"Only public HTTPS links without credentials are permitted")
    _limit(db,thread.id)
    # Reuse the application's approved public-source retriever, including its
    # nonpublic-IP, size, redirect and HTML checks. No private network lookups.
    from .source_retrieval import fetch_public_source
    try:page=fetch_public_source(url)
    except Exception as exc:
        raise HTTPException(422,"Public page could not be retrieved; it may require login, be blocked or be unreachable. Upload a document or paste a short excerpt") from exc
    value=str(page.get("original_content") or "").strip()
    if not value:raise HTTPException(422,"Page has no readable public text. Upload or paste an excerpt")
    title=str(page.get("title") or parsed.hostname)[:260]
    return _store(db,user,p,thread,"LINK",title,url,
          [{"section":"Web page retrieved at "+datetime.now(timezone.utc).isoformat(),"text":value[:MAX_TEXT]}],
          hashlib.sha256(value.encode()).hexdigest())


@router.delete("/{thread_id}/{attachment_id}")
def remove_attachment(thread_id:str,attachment_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=_user_scope(db,user);thread=_thread(db,user,thread_id)
    row=db.query(AssistantChatAttachment).filter_by(id=attachment_id,thread_id=thread.id,user_id=user.id).first()
    if row is None:raise HTTPException(404,"Attachment unavailable")
    _check_scope(row,p);db.delete(row);db.commit()
    return {"deleted":True}


def selected_attachment_evidence(db,user,p,thread_id,ids):
    if not ids:return []
    thread=_thread(db,user,thread_id)
    if not isinstance(ids,list) or len(ids)>MAX_ATTACHMENTS or any(not isinstance(x,str) for x in ids):
        raise HTTPException(422,"Invalid attachment selection")
    rows=db.query(AssistantChatAttachment).filter(
        AssistantChatAttachment.thread_id==thread.id,
        AssistantChatAttachment.user_id==user.id,
        AssistantChatAttachment.id.in_(ids)).all()
    if len(rows)!=len(set(ids)):raise HTTPException(403,"One or more attachments are missing or unauthorized")
    output=[]
    for row in rows:
        _check_scope(row,p)
        for i,section in enumerate(json.loads(row.sections_json or "[]")[:12],1):
            output.append({"record_id":"ATT-"+row.id.replace("-","")+"-S"+str(i),
                "record_type":"CHAT_ATTACHMENT","title":row.title,
                "source_url":row.url if row.kind=="LINK" else "",
                "section":section["section"],"excerpt":section["text"][:1800],
                "source_basis":"USER_SUPPLIED_UNVERIFIED","attachment_id":row.id})
    return output[:45]


def delete_thread_attachments(db,user_id,thread_id):
    db.query(AssistantChatAttachment).filter_by(thread_id=thread_id,user_id=user_id).delete(synchronize_session=False)
