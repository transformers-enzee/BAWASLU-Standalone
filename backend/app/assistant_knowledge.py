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
DOCUMENT_TYPES={"REGULATION","SOP","REPORT","REPORT_TEMPLATE","GUIDANCE","OTHER"}

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
    legal_version_label:Mapped[str]=mapped_column(String(120),default="",nullable=False)
    legal_effective_date:Mapped[str]=mapped_column(String(10),default="",nullable=False)
    legal_election_type:Mapped[str]=mapped_column(String(20),default="UNSPECIFIED",nullable=False)
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
            "legal_version_label":doc.legal_version_label,
            "legal_effective_date":doc.legal_effective_date,
            "legal_election_type":doc.legal_election_type,
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
    legal_version_label:str=Field(default="",max_length=120)
    legal_effective_date:str=Field(default="",max_length=10)
    legal_election_type:str="UNSPECIFIED"
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
    if body.legal_election_type not in {"UNSPECIFIED","PEMILU","PILKADA","BOTH"}:
        raise HTTPException(422,"Invalid legal election type")
    if body.legal_effective_date:
        try:
            datetime.strptime(body.legal_effective_date,"%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(422,"Effective date must use YYYY-MM-DD") from exc
    if body.reviewed and len(body.notes.strip())<12:
        raise HTTPException(422,"Provide review notes (at least 12 characters)")
    row.document_type=body.document_type
    row.issuer=body.issuer.strip()
    row.legal_version_label=body.legal_version_label.strip()
    row.legal_effective_date=body.legal_effective_date
    row.legal_election_type=body.legal_election_type
    row.review_status="OFFICER_REVIEWED" if body.reviewed else "UNREVIEWED"
    row.review_notes=body.notes.strip()
    row.reviewed_by=user.id if body.reviewed else None
    row.reviewed_at=datetime.now(timezone.utc) if body.reviewed else None
    _audit(db,p,row.id,"KNOWLEDGE_DOCUMENT_REVIEW",{
        "review_status":row.review_status,"issuer":row.issuer,
        "document_type":row.document_type,"review_notes":row.review_notes,
        "legal_version_label":row.legal_version_label,
        "legal_effective_date":row.legal_effective_date,
        "legal_election_type":row.legal_election_type})
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

def retrieve_knowledge(db,p,question,limit=6,semantic=True,reviewed_legal_only=False):
    """Private scope-checked retrieval; optionally require reviewed legal PDFs.

    Reviewed means officer metadata review, NOT verification that the law
    remains in force. Keep default broad retrieval for existing AI chat.
    """
    from .assistant_semantic import retrieve_hybrid
    return retrieve_hybrid(db,p,question,limit=limit,semantic=semantic,
                           reviewed_legal_only=reviewed_legal_only)


# Uploaded PDFs are durable chat references, not per-message attachments. The
# assistant automatically retrieves permitted passages for each new turn.
# Follow-ups use the preceding user topic without carrying unrelated old topics.
_FOLLOWUP_RE=re.compile(
    r"^(?:and\b|but\b|then\b|also\b|what about\b|how about\b|what if\b|"
    r"can you elaborate\b|could you expand\b|tell me more\b|"
    r"lalu\b|terus\b|kemudian\b|bagaimana dengan\b|kalau\b|"
    r"dan\b|untuk itu\b|selanjutnya\b|jelaskan lagi\b|"
    r"tolong jelaskan\b|lebih detail\b)",re.I)
_CONTEXT_RE=re.compile(
    r"\b(?:it|its|that|those|these|this|them|there|above|previous|earlier|"
    r"tadi|itu|tersebut|sama|sebelumnya|di atas|yang tadi)\b",re.I)
_OVERVIEW_RE=re.compile(
    r"\b(?:pdf|documents?|dokumen|berkas|lampiran|unggahan|reference|referensi|"
    r"knowledge|sop|manual|pedoman)\b",re.I)
_SUMMARY_RE=re.compile(
    r"\b(?:summary|summarize|summarise|overview|whole|all|entire|"
    r"ringkas|ringkasan|rangkum|rangkuman|seluruh|keseluruhan|isi)\b",re.I)

# Explicit document-page references are source selectors, never a permission grant.
_DOC_PAGE_REF=re.compile(r"(?<![\w-])DOC-([1-9][0-9]{0,11})-P([1-9][0-9]{0,7})(?![\w-])",re.I)

def explicit_pdf_page_refs(question):
    """Distinct positive document/page identifiers mentioned by the officer."""
    return list(dict.fromkeys((int(doc),int(page))
        for doc,page in _DOC_PAGE_REF.findall(str(question or ""))))


def retrieve_exact_pdf_pages(db,p,question,limit=6):
    """All-or-nothing, already-authorized page selection (no semantic API calls).

    Missing, withdrawn, inaccessible and unindexed pages return the same empty
    result; never substitute a different document for an explicit page ID.
    """
    from .assistant_semantic import stitch_pdf_page
    requested=explicit_pdf_page_refs(question)
    if not requested or len(requested)>max(1,min(int(limit),12)):
        return []
    if not has_view_knowledge(p):
        return []
    ids={doc_id for doc_id,_ in requested}
    docs=db.query(KnowledgePDF).filter(KnowledgePDF.id.in_(ids),
                                      KnowledgePDF.active==True).all()
    allowed={doc.id:doc for doc in docs if _visible(p,doc)}
    if len(allowed)!=len(ids):
        return []
    chunks=db.query(KnowledgeChunk).filter(
        KnowledgeChunk.document_id.in_(ids)).order_by(
        KnowledgeChunk.document_id,KnowledgeChunk.page,
        KnowledgeChunk.sequence,KnowledgeChunk.id).all()
    by_page={}
    for chunk in chunks:
        by_page.setdefault((chunk.document_id,chunk.page),[]).append(chunk)
    if any(not by_page.get(key) for key in requested):
        return []
    results=[]
    for doc_id,page in requested:
        doc=allowed[doc_id]
        excerpt=stitch_pdf_page(by_page[(doc_id,page)])
        if not excerpt.strip():
            return []
        results.append({
            "record_id":f"DOC-{doc.id}-P{page}",
            "record_type":"PDF_KNOWLEDGE","document_id":doc.id,
            "title":doc.title,"filename":doc.filename,"page":page,
            "source_excerpt":excerpt,
            "source_url":f"/api/assistant-knowledge/{doc.id}/download",
            "scope":doc.scope,"province":doc.province,
            "document_type":doc.document_type,"issuer":doc.issuer,
            "legal_version_label":doc.legal_version_label,
            "legal_effective_date":doc.legal_effective_date,
            "legal_election_type":doc.legal_election_type,
            "review_status":doc.review_status,
            "legal_currentness_verified":False,
            "verification_status":"UPLOADED_DOCUMENT_NOT_LEGAL_VALIDATION",
            "document_is_authority_unverified":doc.review_status!="OFFICER_REVIEWED",
            "match_method":"EXACT_AUTHORIZED_PAGE_ID",
        })
    return results


def authorized_reference_catalog(db,p,limit=24):
    """Only visible documents are available to the chat or its catalog."""
    _access(p)
    docs=db.query(KnowledgePDF).filter_by(active=True).order_by(
        KnowledgePDF.id.desc()).limit(150).all()
    return [{"id":doc.id,"title":doc.title,"pages":doc.pages,
             "document_type":doc.document_type,"review_status":doc.review_status,
             "issuer":doc.issuer}
            for doc in docs if _visible(p,doc)][:max(1,min(int(limit),24))]

def _last_substantive_user_question(previous,history):
    candidates=[str(previous or "").strip()]
    if isinstance(history,list):
        candidates += [str(row.get("text") or "").strip()
                       for row in reversed(history[-12:]) if isinstance(row,dict)
                       and row.get("role")=="user"]
    return next((q[:450] for q in candidates
                 if len(q)>=10 and len(re.findall(r"[\w]{3,}",q))>=2),"")

def _document_overview(db,p,limit):
    """Bounded, page-spread excerpts for broad 'summarize my PDF' questions."""
    docs=db.query(KnowledgePDF).filter_by(active=True).order_by(
        KnowledgePDF.id.desc()).limit(150).all()
    visible=[doc for doc in docs if _visible(p,doc)][:2]
    if not visible:return []
    from .assistant_semantic import stitch_pdf_page
    candidates=[]
    for doc in visible:
        chunks=db.query(KnowledgeChunk).filter_by(document_id=doc.id).order_by(
            KnowledgeChunk.page,KnowledgeChunk.sequence,KnowledgeChunk.id).all()
        if not chunks:continue
        by_page={}
        for chunk in chunks:
            by_page.setdefault(chunk.page,[]).append(chunk)
        pages=sorted(by_page)
        # Sample across the whole document; preserve every selected page's
        # indexed chunks rather than silently omitting the remaining text.
        slots=min(5,len(pages))
        chosen=[pages[round(i*(len(pages)-1)/max(1,slots-1))]
                for i in range(slots)]
        candidates.extend((doc,page,by_page[page]) for page in dict.fromkeys(chosen))
    output=[]
    for doc,page,page_chunks in candidates[:max(1,min(limit,10))]:
        excerpt=stitch_pdf_page(page_chunks,max_chars=3000)
        if not excerpt.strip():continue
        output.append({
            "record_id":f"DOC-{doc.id}-P{page}",
            "record_type":"PDF_KNOWLEDGE","document_id":doc.id,
            "title":doc.title,"filename":doc.filename,"page":page,
            "source_excerpt":excerpt,
            "source_url":f"/api/assistant-knowledge/{doc.id}/download",
            "scope":doc.scope,"province":doc.province,
            "document_type":doc.document_type,"issuer":doc.issuer,
            "legal_version_label":doc.legal_version_label,
            "legal_effective_date":doc.legal_effective_date,
            "legal_election_type":doc.legal_election_type,
            "review_status":doc.review_status,
            "legal_currentness_verified":False,
            "verification_status":"UPLOADED_DOCUMENT_NOT_LEGAL_VALIDATION",
            "document_is_authority_unverified":doc.review_status!="OFFICER_REVIEWED",
            "match_method":"DOCUMENT_OVERVIEW"
        })
    return output

def retrieve_chat_knowledge(db,p,question,previous="",history=None,limit=6,
                            semantic=True):
    """Automatic PDF grounding for chat, including document-related follow-ups.

    Never passes previous conversation content to a private document search
    outside the user's authorized scope. Keyword-only documents cost no
    embedding credits; semantic search requires a pre-indexed document.
    """
    q=str(question or "").strip()
    if not q:return []
    if not has_view_knowledge(p):
        return []
    if explicit_pdf_page_refs(q):
        return retrieve_exact_pdf_pages(db,p,q,limit=limit)
    previous_topic=_last_substantive_user_question(previous,history)
    followup=(bool(_FOLLOWUP_RE.search(q) or _CONTEXT_RE.search(q)) and
              bool(previous_topic) and previous_topic.casefold()!=q.casefold())
    lookup=(q+" "+previous_topic)[:950] if followup else q[:500]
    results=retrieve_knowledge(db,p,lookup,limit=limit,semantic=semantic)
    # Preserve both the new turn's intent and its prior PDF topic: a combined
    # query can otherwise rank only pages about the previous question.
    if followup:
        current=retrieve_knowledge(db,p,q,limit=max(3,limit//2),semantic=False)
        collected={}
        for row in current+results:collected.setdefault(row["record_id"],row)
        results=list(collected.values())[:limit]
    # The user can request a document-wide explanation conversationally.
    if not results and _OVERVIEW_RE.search(q) and _SUMMARY_RE.search(q):
        results=_document_overview(db,p,limit)
    return results

def has_view_knowledge(p):
    return has(p,"view_intelligence")
