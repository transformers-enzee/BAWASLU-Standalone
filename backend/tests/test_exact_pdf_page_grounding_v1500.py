"""v150.0: exact permission-scoped PDF page selection and complete overview pages."""
from app.assistant_knowledge import (
    KnowledgePDF,KnowledgeChunk,retrieve_chat_knowledge,
    explicit_pdf_page_refs,retrieve_exact_pdf_pages,_document_overview)
from app.assistant_response_profile import choose_response_profile,PDF_GUIDANCE
from test_oversight_knowledge_sentiment import db,p

def pdf(db,title,scope,province,texts,active=True):
    import hashlib
    document=KnowledgePDF(
        title=title,filename="review.pdf",scope=scope,province=province,
        content_sha256=hashlib.sha256((title+province).encode()).hexdigest(),
        content_bytes=b"%PDF-fixture",pages=max(1,max((z[0] for z in texts),default=1)),
        extracted_chars=100,uploaded_by=1,active=active,
        review_status="UNREVIEWED",document_type="REGULATION")
    db.add(document);db.flush()
    for page,sequence,value in texts:
        db.add(KnowledgeChunk(document_id=document.id,page=page,
                              sequence=sequence,text_content=value))
    db.commit()
    return document

def test_explicit_pdf_page_selects_only_named_authorized_page(db):
    d=pdf(db,"Riau SOP","PROVINCE","Riau",[
      (1,1,"Unrelated introduction"),
      (2,1,"Preliminary caseworker guidance."),
      (2,2,"Supporting evidence and review are mandatory.")])
    q=f"Explain [DOC-{d.id}-P2] according to BAWASLU's PDF"
    assert explicit_pdf_page_refs(q)==[(d.id,2)]
    assert choose_response_profile(q,analysis_mode="GENERAL")==PDF_GUIDANCE
    rows=retrieve_chat_knowledge(db,p(db,2),q)
    assert len(rows)==1 and rows[0]["record_id"]==f"DOC-{d.id}-P2"
    assert "Preliminary caseworker guidance." in rows[0]["source_excerpt"]
    assert "Supporting evidence and review" in rows[0]["source_excerpt"]
    assert rows[0]["legal_currentness_verified"] is False
    assert rows[0]["match_method"]=="EXACT_AUTHORIZED_PAGE_ID"
    assert retrieve_chat_knowledge(db,p(db,3),q)==[]

def test_missing_or_withdrawn_exact_page_fails_closed_without_substitution(db):
    d=pdf(db,"Authorized Riau","PROVINCE","Riau",[(1,1,"Relevant official guidance")])
    b=pdf(db,"Other province","PROVINCE","Bali",[(1,1,"Different text")])
    mixed=f"Compare DOC-{d.id}-P1 with DOC-{b.id}-P1"
    assert retrieve_chat_knowledge(db,p(db,2),mixed)==[]
    assert retrieve_chat_knowledge(db,p(db,2),f"DOC-{d.id}-P2")==[]
    assert retrieve_chat_knowledge(db,p(db,2),f"DOC-{d.id}-P1 DOC-{d.id}-P2")==[]
    d.active=False;db.commit()
    assert retrieve_chat_knowledge(db,p(db,2),f"DOC-{d.id}-P1")==[]

def test_explicit_too_many_pages_does_not_return_partial_selection(db):
    d=pdf(db,"National Guide","NATIONAL","",[(i,1,f"Page {i} excerpt") for i in range(1,9)])
    query=" ".join(f"DOC-{d.id}-P{i}" for i in range(1,8))
    assert retrieve_exact_pdf_pages(db,p(db,1),query,limit=6)==[]

def test_document_overview_uses_full_indexed_chunks_from_each_page(db):
    d=pdf(db,"Riau overview","PROVINCE","Riau",[
      (1,1,"Part one describes the original standard."),
      (1,2,"Part two contains additional required documentation."),
      (3,1,"Later page discusses the review process.")])
    out=_document_overview(db,p(db,2),limit=6)
    first=next(x for x in out if x["record_id"]==f"DOC-{d.id}-P1")
    assert "Part one describes" in first["source_excerpt"]
    assert "Part two contains" in first["source_excerpt"]
    assert first["match_method"]=="DOCUMENT_OVERVIEW"
    assert _document_overview(db,p(db,3),limit=6)==[]
