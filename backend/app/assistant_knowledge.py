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
from pydantic import BaseModel,Field
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
DOCUMENT_TYPES={"REGULATION","SOP","REPORT","GUIDANCE","OTHER"}

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
    document_type:Mapped[str]=mapped_column(String(24),default="OTHER",nullable=False)
    issuer:Mapped[str]=mapped_column(String(220),default="",nullable=False)
    review_status:Mapped[str]=mapped_column(String(24),default="UNREVIEWED",nullable=False)
    review_notes:Mapped[str]=mapped_column(Text,default="",nullable=False)
    reviewed_by:Mapped[int | None]=mapped_column(Integer,ForeignKey("users.id"),nullable=True)
    reviewed_at:Mapped[datetime | None]=mapped_column(DateTime,nullable=True)
    embedding_status:Mapped[str]=mapped_column(String(24),default="NOT_INDEXED",nullable=False)
    embedding_model:Mapped[str]=mapped_column(String(64),default="",nullable=False)

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
        "document_type":doc.document_type,"issuer":doc.issuer,
        "review_status":doc.review_status,"review_notes":doc.review_notes,
        "reviewed_at":doc.reviewed_at.isoformat() if doc.reviewed_at else None,
        "embedding_status":doc.embedding_status,"embedding_model":doc.embedding_model,
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
                     document_type:str=Form("OTHER"),issuer:str=Form(""),
                     semantic_index:bool=Form(False),
                     user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user);_access(p)
    dest=_allow_upload(p,scope,province)
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(422,"Invalid document type")
    if len(issuer)>220:
        raise HTTPException(422,"Issuer field too long")
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
        uploaded_by=user.id,active=True,document_type=document_type,
        issuer=issuer.strip(),review_status="UNREVIEWED",
        embedding_status="NOT_INDEXED")
    db.add(row);db.flush()
    stored_chunks=[]
    for seq,(page,excerpt) in enumerate(chunks,1):
        chunk=KnowledgeChunk(document_id=row.id,page=page,sequence=seq,
                             text_content=excerpt)
        db.add(chunk)
        stored_chunks.append(chunk)
    indexed,provider_called=False,False
    if semantic_index:
        from .assistant_semantic import index_document
        indexed,provider_called=index_document(db,row,stored_chunks)
    _audit(db,p,row.id,"KNOWLEDGE_PDF_UPLOADED",
           {"title":heading,"scope":scope,"province":dest,"sha256":digest,
            "pages":pages,"chunks":len(chunks),
            "semantic_index_requested":semantic_index,"semantic_indexed":indexed})
    db.commit()
    return {"document":_view(row),"duplicate":False,
            "indexed_chunks":len(chunks),"semantic_indexed":indexed,
            "paid_provider_called":provider_called}

@router.get("/documents")
def list_knowledge(user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user);_access(p)
    candidates=db.query(KnowledgePDF).filter_by(active=True).order_by(
        KnowledgePDF.id.desc()).limit(250).all()
    return {"documents":[_view(row) for row in candidates if _visible(p,row)],
            "can_upload":has(p,"upload_evidence") and has(p,"add_intelligence"),
            "can_review":has(p,"human_validation"),
            "default_scope":_scope(p),"default_province":p.get("province") or "",
            "paid_provider_called":False}

class ReviewBody(BaseModel):
    document_type:str
    issuer:str=""
    notes:str=Field(default="",max_length=1500)
    reviewed:bool=False

@router.post("/{document_id}/review")
def review_pdf(document_id:int,body:ReviewBody,user:User=Depends(current_user),
               db:Session=Depends(get_db)):
    p=profile(db,user)
    row=db.get(KnowledgePDF,document_id)
    if not _visible(p,row):
        raise HTTPException(404,"Document not accessible")
    if not has(p,"human_validation"):
        raise HTTPException(403,"Officer review permission is required")
    if body.document_type not in DOCUMENT_TYPES or len(body.issuer)>220:
        raise HTTPException(422,"Invalid document metadata")
    if body.reviewed and len(body.notes.strip())<12:
        raise HTTPException(422,"Provide review notes (at least 12 characters)")
    row.document_type=body.document_type
    row.issuer=body.issuer.strip()
    row.review_status="OFFICER_REVIEWED" if body.reviewed else "UNREVIEWED"
    row.review_notes=body.notes.strip()
    row.reviewed_by=user.id if body.reviewed else None
    row.reviewed_at=datetime.now(timezone.utc) if body.reviewed else None
    _audit(db,p,row.id,"KNOWLEDGE_DOCUMENT_REVIEW",{
        "review_status":row.review_status,"issuer":row.issuer,
        "document_type":row.document_type,"review_notes":row.review_notes})
    db.commit()
    return {"document":_view(row),"legal_currentness_verified":False}

@router.post("/{document_id}/semantic-index")
def index_pdf(document_id:int,user:User=Depends(current_user),
              db:Session=Depends(get_db)):
    p=profile(db,user)
    row=db.get(KnowledgePDF,document_id)
    if not _visible(p,row):
        raise HTTPException(404,"Document not accessible")
    if not has(p,"upload_evidence") or not (
        row.uploaded_by==user.id or has(p,"administration")):
        raise HTTPException(403,"Only the uploader or administrator may index this PDF")
    if row.embedding_status=="READY":
        return {"document":_view(row),"indexed":True,"already_indexed":True,
                "paid_provider_called":False}
    from .assistant_semantic import index_document
    chunks=db.query(KnowledgeChunk).filter_by(document_id=row.id).order_by(
        KnowledgeChunk.id).all()
    indexed,provider_called=index_document(db,row,chunks)
    _audit(db,p,row.id,"KNOWLEDGE_SEMANTIC_INDEX",{
        "indexed":indexed,"status":row.embedding_status,"model":row.embedding_model})
    db.commit()
    return {"document":_view(row),"indexed":indexed,
            "paid_provider_called":provider_called}

@router.get("/search-preview")
def search_preview(question:str,semantic:bool=False,user:User=Depends(current_user),
                   db:Session=Depends(get_db)):
    """Officer tests PDF retrieval without an assistant completion call."""
    p=profile(db,user)
    _access(p)
    if not question.strip() or len(question)>500:
        raise HTTPException(422,"Question must be between 1 and 500 characters")
    docs=retrieve_knowledge(db,p,question,limit=6,semantic=semantic)
    return {"matches":[{"record_id":x["record_id"],"title":x["title"],
        "page":x["page"],"source_excerpt":x["source_excerpt"][:520],
        "document_id":x["document_id"],"match_method":x["match_method"],
        "review_status":x["review_status"]} for x in docs],
        "count":len(docs),"semantic_requested":semantic,
        "no_completion_call":True,
        "note":"Retrieved document passages are references, not confirmation of current law."}

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

def retrieve_knowledge(db,p,question,limit=6,semantic=True):
    """Private, permission-filtered hybrid search with lexical fallback."""
    from .assistant_semantic import retrieve_hybrid
    return retrieve_hybrid(db,p,question,limit=limit,semantic=semantic)
