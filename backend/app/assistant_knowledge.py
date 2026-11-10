"""Private PDF knowledge library used as cited retrieval evidence, NOT model training.

Stored in PostgreSQL (Supabase, the primary DB). No public file URL, provider
upload, OCR, web indexing, or silent reprocessing. Byte/page/text limits protect
the service, and every read is officer scope-checked.
"""
import hashlib
import io
import re
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from fastapi.responses import Response
from sqlalchemy import DateTime,ForeignKey,Integer,LargeBinary,String,Text
from sqlalchemy.orm import Mapped,mapped_column,Session
from .db import Base,get_db
from .auth import current_user
from .access import profile,has
from .models import User

router=APIRouter(prefix="/api/assistant-knowledge",tags=["assistant-knowledge"])
MAX_BYTES=5*1024*1024
MAX_PAGES=80
MAX_CHARS=160000

class KnowledgePDF(Base):
    __tablename__="assistant_knowledge_pdfs"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    title:Mapped[str]=mapped_column(String(240),nullable=False)
    filename:Mapped[str]=mapped_column(String(220),nullable=False)
    scope:Mapped[str]=mapped_column(String(20),nullable=False,default="NATIONAL")
    province:Mapped[str]=mapped_column(String(128),nullable=False,default="")
    content_sha256:Mapped[str]=mapped_column(String(64),nullable=False,index=True)
    content_bytes:Mapped[bytes]=mapped_column(LargeBinary,nullable=False)
    pages:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    extracted_chars:Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    uploaded_by:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False)
    uploaded_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)
    active:Mapped[bool]=mapped_column(default=True,nullable=False)

class KnowledgeChunk(Base):
    __tablename__="assistant_knowledge_chunks"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    document_id:Mapped[int]=mapped_column(Integer,ForeignKey("assistant_knowledge_pdfs.id"),index=True,nullable=False)
    page:Mapped[int]=mapped_column(Integer,nullable=False)
    sequence:Mapped[int]=mapped_column(Integer,nullable=False)
    text_content:Mapped[str]=mapped_column(Text,nullable=False)

def _access(p):
    if not has(p,"view_intelligence"):
        raise HTTPException(403,"Knowledge library access required")

def _scope(p):
    return "NATIONAL" if p.get("geographic_scope")=="Nationwide" else "PROVINCE"

def _visible(p,doc):
    if not has(p,"view_intelligence") or not doc or not doc.active:
        return False
    if p.get("geographic_scope")=="Nationwide":
        return True
    province=(p.get("province") or "").casefold()
    return doc.scope=="NATIONAL" or (
        doc.scope=="PROVINCE" and bool(province) and doc.province.casefold()==province)

def _allow_upload(p,scope,province):
    if not has(p,"upload_evidence") or not has(p,"add_intelligence"):
        raise HTTPException(403,"Officer document upload permission required")
    if scope=="NATIONAL":
        if p.get("geographic_scope")!="Nationwide":
            raise HTTPException(403,"Only national officers can publish national knowledge")
        return ""
    if scope!="PROVINCE":
        raise HTTPException(422,"Choose NATIONAL or PROVINCE scope")
    if not province.strip():
        raise HTTPException(422,"Select the document's province")
    if p.get("geographic_scope")!="Nationwide" and (
        province.casefold()!=str(p.get("province") or "").casefold()
    ):
        raise HTTPException(403,"Cannot upload another province's knowledge")
    return province

def _reader_pages(data):
    from pypdf import PdfReader
    try:
        reader=PdfReader(io.BytesIO(data),strict=False)
        if reader.is_encrypted:
            raise HTTPException(422,"Password-protected PDFs are not supported")
        if not 1<=len(reader.pages)<=MAX_PAGES:
            raise HTTPException(422,f"PDF page limit is {MAX_PAGES}")
        output=[]
        total=0
        for number,page in enumerate(reader.pages,1):
            raw=" ".join(str(page.extract_text() or "").split())
            if not raw:
                continue
            total+=len(raw)
            if total>MAX_CHARS:
                raise HTTPException(422,"PDF contains too much extractable text; split the file")
            # Chunk by page, maintaining stable page citations.
            for start in range(0,len(raw),1400):
                excerpt=raw[start:start+1600]
                if excerpt.strip():
                    output.append((number,excerpt))
        if not output:
            raise HTTPException(422,"No selectable text was found. Scanned PDF images require OCR before upload")
        return len(reader.pages),total,output
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422,"Invalid or unreadable PDF file") from exc

def _view(doc):
    return {"id":doc.id,"title":doc.title,"filename":doc.filename,
        "scope":doc.scope,"province":doc.province,"pages":doc.pages,
        "extracted_chars":doc.extracted_chars,"uploaded_at":doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        "uploaded_by":doc.uploaded_by,"active":doc.active,
        "download_url":f"/api/assistant-knowledge/{doc.id}/download"}

def _audit(db,p,subject,action,changes):
    import json
    from .models import AuditEvent
    db.add(AuditEvent(subject_type="AssistantKnowledgePDF",subject_id=str(subject),
        actor_id=p["id"],actor_name=p["name"],action=action,
        changes_json=json.dumps(changes,ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat()))

@router.post("/upload")
async def upload_pdf(file:UploadFile=File(...),title:str=Form(""),
                     scope:str=Form("NATIONAL"),province:str=Form(""),
                     user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user);_access(p)
    dest=_allow_upload(p,scope,province)
    name=(file.filename or "").replace("\\","/").split("/")[-1][:220]
    if not name.lower().endswith(".pdf"):
        raise HTTPException(422,"Only PDF files are accepted")
    if file.content_type not in ("application/pdf","application/octet-stream",None):
        raise HTTPException(422,"Invalid PDF content type")
    data=await file.read(MAX_BYTES+1)
    if not data.startswith(b"%PDF-") or len(data)>MAX_BYTES:
        raise HTTPException(422,"Invalid PDF signature or PDF exceeds 5 MB")
    digest=hashlib.sha256(data).hexdigest()
    duplicate=db.query(KnowledgePDF).filter_by(content_sha256=digest,
        scope=scope,province=dest,active=True).first()
    if duplicate and _visible(p,duplicate):
        return {"document":_view(duplicate),"duplicate":True,"paid_provider_called":False}
    pages,characters,chunks=_reader_pages(data)
    heading=" ".join((title.strip() or name[:-4]).split())[:240]
    if not heading:
        raise HTTPException(422,"Provide a document title")
    row=KnowledgePDF(title=heading,filename=name,scope=scope,province=dest,
        content_sha256=digest,content_bytes=data,pages=pages,extracted_chars=characters,
        uploaded_by=user.id,active=True)
    db.add(row);db.flush()
    for seq,(page,excerpt) in enumerate(chunks,1):
        db.add(KnowledgeChunk(document_id=row.id,page=page,sequence=seq,
                              text_content=excerpt))
    _audit(db,p,row.id,"KNOWLEDGE_PDF_UPLOADED",
           {"title":heading,"scope":scope,"province":dest,"sha256":digest,
            "pages":pages,"chunks":len(chunks)})
    db.commit()
    return {"document":_view(row),"duplicate":False,
            "indexed_chunks":len(chunks),"paid_provider_called":False}

@router.get("/documents")
def list_knowledge(user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user);_access(p)
    candidates=db.query(KnowledgePDF).filter_by(active=True).order_by(
        KnowledgePDF.id.desc()).limit(250).all()
    return {"documents":[_view(row) for row in candidates if _visible(p,row)],
            "can_upload":has(p,"upload_evidence") and has(p,"add_intelligence"),
            "default_scope":_scope(p),"default_province":p.get("province") or "",
            "paid_provider_called":False}

@router.get("/{document_id}/download")
def download_pdf(document_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user);_access(p)
    row=db.get(KnowledgePDF,document_id)
    if not _visible(p,row):
        raise HTTPException(404,"Document not accessible")
    return Response(row.content_bytes,media_type="application/pdf",
        headers={"Content-Disposition":f'attachment; filename="bawaslu-reference-{document_id}.pdf"',
                 "Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})

@router.delete("/{document_id}")
def deactivate_pdf(document_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    row=db.get(KnowledgePDF,document_id)
    if not _visible(p,row):
        raise HTTPException(404,"Document not accessible")
    if not has(p,"upload_evidence") or (
        str(user.id)!=str(row.uploaded_by) and not has(p,"administration")):
        raise HTTPException(403,"Only the uploading officer or administrator can deactivate the PDF")
    row.active=False
    _audit(db,p,row.id,"KNOWLEDGE_PDF_DEACTIVATED",{"scope":row.scope})
    db.commit()
    return {"active":False,"paid_provider_called":False}

def retrieve_knowledge(db,p,question,limit=6):
    """Bounded, permission-scoped lexical retrieval; no paid AI or web calls."""
    if not has(p,"view_intelligence"):return []
    from .intelligence_assistant import STOPWORDS
    words=[w for w in re.findall(r"[\w]{3,}",str(question or "").casefold())
           if w not in STOPWORDS and not w.isnumeric()]
    terms=list(dict.fromkeys(words))[:12]
    if not terms:
        return []
    all_docs=[d for d in db.query(KnowledgePDF).filter_by(active=True).order_by(
        KnowledgePDF.id.desc()).limit(80).all() if _visible(p,d)]
    if not all_docs:return []
    ids=[d.id for d in all_docs]
    docs={d.id:d for d in all_docs}
    from sqlalchemy import or_
    q=db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id.in_(ids))
    q=q.filter(or_(*[KnowledgeChunk.text_content.ilike("%"+word.replace("%","").replace("_","")+"%")
                      for word in terms[:8]]))
    # Enforce a processing bound before scoring so an oversized library cannot
    # exhaust the web worker.
    candidates=q.order_by(KnowledgeChunk.id.desc()).limit(240).all()
    ranked=[]
    for row in candidates:
        d=docs[row.document_id]
        hay=row.text_content.casefold()
        title=d.title.casefold()
        hits=sum(3 if term in title else 1 for term in terms if term in hay or term in title)
        if not hits:continue
        ranked.append((hits,row.id,row,d))
    ranked.sort(reverse=True,key=lambda item:(item[0],item[1]))
    unique=set();out=[]
    for score,_,chunk,doc in ranked:
        key=(doc.id,chunk.page)
        if key in unique:continue
        unique.add(key)
        out.append({"record_id":f"DOC-{doc.id}-P{chunk.page}",
            "record_type":"PDF_KNOWLEDGE","document_id":doc.id,"title":doc.title,
            "filename":doc.filename,"page":chunk.page,"scope":doc.scope,
            "province":doc.province,"source_excerpt":chunk.text_content[:1500],
            "source_url":f"/api/assistant-knowledge/{doc.id}/download",
            "publication_date":"","verification_status":"UPLOADED_DOCUMENT_NOT_LEGAL_VALIDATION",
            "document_is_authority_unverified":True})
        if len(out)>=limit:break
    return out
