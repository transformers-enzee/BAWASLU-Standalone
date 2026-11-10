"""Permission-scoped semantic PDF indexing and hybrid retrieval.

OpenAI embeddings are only created after explicit officer opt-in. Existing
keyword retrieval remains available if vectors are missing or the provider is
unavailable. No private document is fetched before scope checks.
"""
import json
import logging
import os
import re

import httpx
from sqlalchemy import bindparam, text

EMBED_MODEL="text-embedding-3-small"
EMBED_DIMS=1536
MAX_VECTOR_CHUNKS=120
logger=logging.getLogger(__name__)

def embeddings(values):
    api_key=os.getenv("OPENAI_API_KEY","").strip()
    if not api_key:
        raise RuntimeError("Semantic indexing requires configured embedding provider")
    if not values:return []
    url=os.getenv("OPENAI_BASE_URL","https://api.openai.com/v1").rstrip("/")+"/embeddings"
    output=[]
    with httpx.Client(timeout=35.0) as client:
        for offset in range(0,len(values),48):
            batch=values[offset:offset+48]
            response=client.post(url,
                headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"},
                json={"model":EMBED_MODEL,"input":batch,"encoding_format":"float"})
            response.raise_for_status()
            items=sorted(response.json().get("data") or [],key=lambda x:x.get("index",-1))
            if len(items)!=len(batch):
                raise ValueError("Unexpected embedding response count")
            for index,item in enumerate(items):
                vec=item.get("embedding")
                if item.get("index")!=index or not isinstance(vec,list) or len(vec)!=EMBED_DIMS:
                    raise ValueError("Unexpected embedding dimensions")
                output.append(vec)
    return output

def vector_supported(db):
    return bool(db.bind and db.bind.dialect.name=="postgresql")

def index_document(db,document,chunks):
    """Return (indexed, provider_called). One failed savepoint cannot lose the PDF."""
    if not vector_supported(db):
        document.embedding_status="UNSUPPORTED"
        return False,False
    if len(chunks)>MAX_VECTOR_CHUNKS:
        document.embedding_status="TOO_LARGE"
        return False,False
    if not os.getenv("OPENAI_API_KEY","").strip():
        document.embedding_status="NOT_CONFIGURED"
        return False,False
    provider_called=False
    document.embedding_status="INDEXING"
    db.flush()
    try:
        provider_called=True
        vectors=embeddings([item.text_content for item in chunks])
        if len(vectors)!=len(chunks):
            raise ValueError("Mismatched document index count")
        with db.begin_nested():
            for item,vec in zip(chunks,vectors):
                db.execute(text(
                    "UPDATE public.assistant_knowledge_chunks "
                    "SET embedding=CAST(:vector AS extensions.vector) "
                    "WHERE id=:chunk_id AND document_id=:document_id"),
                    {"vector":json.dumps(vec,separators=(",",":")),
                     "chunk_id":item.id,"document_id":document.id})
        document.embedding_status="READY"
        document.embedding_model=EMBED_MODEL
        return True,provider_called
    except Exception:
        logger.exception("ASSISTANT_DOCUMENT_INDEX_ERROR document=%s",document.id)
        document.embedding_status="FAILED"
        document.embedding_model=""
        return False,provider_called

def lexical_search(db,documents,question,terms):
    from .assistant_knowledge import KnowledgeChunk
    from sqlalchemy import or_
    ids=[doc.id for doc in documents]
    if not ids or not terms:return []
    rows=db.query(KnowledgeChunk).filter(
        KnowledgeChunk.document_id.in_(ids),
        or_(*[KnowledgeChunk.text_content.ilike(
            "%"+term.replace("%","").replace("_","")+"%") for term in terms[:10]])
    ).order_by(KnowledgeChunk.id.desc()).limit(240).all()
    docs={d.id:d for d in documents}
    ranked=[]
    phrase=str(question or "").casefold().strip()
    for row in rows:
        doc=docs[row.document_id]
        body=row.text_content.casefold()
        heading=doc.title.casefold()
        score=sum(3 if term in heading else 1 for term in terms if term in body or term in heading)
        if phrase and phrase in body:
            score+=5
        if score>0:ranked.append((score,row.id,row))
    ranked.sort(key=lambda v:(-v[0],-v[1]))
    return [x[2] for x in ranked[:45]]

def semantic_search(db,documents,question):
    """Top-K cosine search in pgvector, with authorized document IDs in SQL."""
    if not vector_supported(db) or not os.getenv("OPENAI_API_KEY","").strip():
        return []
    indexed=[d.id for d in documents
        if d.embedding_status=="READY" and d.embedding_model==EMBED_MODEL]
    if not indexed:return []
    from .assistant_knowledge import KnowledgeChunk
    try:
        [vector]=embeddings([str(question or "")[:500]])
        query=text("""
            SELECT c.id, (c.embedding <=> CAST(:vector AS extensions.vector)) AS distance
            FROM public.assistant_knowledge_chunks c
            WHERE c.document_id IN :document_ids AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:vector AS extensions.vector)
            LIMIT 32
        """).bindparams(bindparam("document_ids",expanding=True))
        # Protect the surrounding assistant DB transaction if vector SQL fails.
        with db.begin_nested():
            rows=db.execute(query,{"vector":json.dumps(vector,separators=(",",":")),
               "document_ids":indexed}).all()
        ranked=[int(x[0]) for x in rows if x[1] is not None and float(x[1])<=0.72]
        if not ranked:return []
        found=db.query(KnowledgeChunk).filter(KnowledgeChunk.id.in_(ranked)).all()
        by_id={row.id:row for row in found}
        return [by_id[rid] for rid in ranked if rid in by_id]
    except Exception:
        logger.exception("ASSISTANT_SEMANTIC_QUERY_FAILED")
        return []

def merge_rankings(lexical,semantic,documents,limit):
    """Rank-fusion: matches from both strategies get a relevance advantage."""
    indexed={doc.id:doc for doc in documents}
    scores={}
    for group,method in ((lexical,"KEYWORD"),(semantic,"SEMANTIC")):
        for rank,chunk in enumerate(group,1):
            item=scores.setdefault(chunk.id,{"chunk":chunk,"score":0.0,"methods":set()})
            item["score"]+=1/(40+rank)
            item["methods"].add(method)
    ranking=[]
    for item in scores.values():
        chunk=item["chunk"]
        doc=indexed.get(chunk.document_id)
        if not doc:continue
        weight=1.10 if doc.review_status=="OFFICER_REVIEWED" else 1.0
        ranking.append((item["score"]*weight,chunk.id,chunk,doc,item["methods"]))
    ranking.sort(key=lambda x:(-x[0],-x[1]))
    out=[]
    used_pages=set()
    for score,_,chunk,doc,methods in ranking:
        key=(doc.id,chunk.page)
        if key in used_pages:continue
        used_pages.add(key)
        out.append({
            "record_id":f"DOC-{doc.id}-P{chunk.page}",
            "record_type":"PDF_KNOWLEDGE","document_id":doc.id,
            "title":doc.title,"filename":doc.filename,"page":chunk.page,
            "source_excerpt":chunk.text_content[:1500],
            "source_url":f"/api/assistant-knowledge/{doc.id}/download",
            "scope":doc.scope,"province":doc.province,"publication_date":"",
            "document_type":doc.document_type,"issuer":doc.issuer,
            "review_status":doc.review_status,
            "legal_currentness_verified":False,
            "verification_status":"UPLOADED_DOCUMENT_NOT_LEGAL_VALIDATION",
            "document_is_authority_unverified":doc.review_status!="OFFICER_REVIEWED",
            "match_method":"HYBRID" if len(methods)>1 else next(iter(methods))
        })
        if len(out)>=max(1,min(int(limit),12)):break
    return out

def retrieve_hybrid(db,profile,question,limit=6,semantic=True):
    from .assistant_knowledge import KnowledgePDF,_visible
    from .intelligence_assistant import STOPWORDS
    from .access import has
    if not has(profile,"view_intelligence"):return []
    tokens=[word for word in re.findall(r"[\w]{3,}",str(question or "").casefold())
            if word not in STOPWORDS and not word.isnumeric()]
    terms=list(dict.fromkeys(tokens))[:16]
    if not terms:return []
    docs=[doc for doc in db.query(KnowledgePDF).filter_by(active=True).order_by(
        KnowledgePDF.id.desc()).limit(150).all() if _visible(profile,doc)]
    if not docs:return []
    lexical=lexical_search(db,docs,question,terms)
    semantic_rows=semantic_search(db,docs,question) if semantic else []
    return merge_rankings(lexical,semantic_rows,docs,limit)
