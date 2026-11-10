"""Audited sentiment correction, PDF RAG scope, and separate legal/platform triage."""
import io
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pypdf import PdfWriter
from app.db import Base
from app.models import (User,AccessGrant,MonitoringCampaign,SocialListeningResult,SocialListeningRun,
                        CampaignEvidence,EvidenceAssessment)
from app.access import default_permissions,profile
from app.officer_sentiment import (CorrectionBody,correct_sentiment,
    latest_corrections,OfficerSentimentCorrection)
from app.campaigns import _latest_sentiment,_sentiment_details
from app.assistant_knowledge import (KnowledgePDF,KnowledgeChunk,retrieve_knowledge,_reader_pages,
    _visible,_allow_upload,download_pdf,list_knowledge,upload_pdf)
from app.oversight_legal import legal_snapshot

@pytest.fixture()
def db():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db=Session(engine)
    for uid,role,scope,province in [(1,"National Administrator","Nationwide",""),
                                    (2,"Provincial Analyst","Province","Riau"),
                                    (3,"Provincial Analyst","Province","Bali"),
                                    (4,"Viewer","Nationwide","")]:
        db.add(User(id=uid,email=f"test{uid}@invalid.local",full_name=f"Officer {uid}",password_hash="unused"))
        db.add(AccessGrant(user_id=uid,access_role=role,geographic_scope=scope,
                           province=province,status="Active",
                           permissions_json=json.dumps(default_permissions(role))))
    db.add(MonitoringCampaign(id=70,name="Riau campaign",province="Riau",created_by="1"))
    # The test fixture records are linked to one campaign; the raw source text
    # and original AI annotation remain unchanged after an officer override.
    db.add(SocialListeningResult(id=200,run_id=1,platform="instagram",
        text_content="Dugaan pelanggaran pemilu di Riau melibatkan Gibran dan laporan BAWASLU",
        canonical_url="https://example.org/200"))
    db.add(CampaignEvidence(campaign_id=70,result_id=200))
    db.add(EvidenceAssessment(campaign_id=70,result_id=200,assessment_version=1,
        relevance_label="RELEVANT",sentiment="NEGATIVE",sentiment_model="GPT-TEST"))
    db.commit()
    yield db
    db.close()

def user(db,id):return db.get(User,id)
def p(db,id):return profile(db,user(db,id))

def test_officer_correction_is_append_only_and_shared_by_campaign_views(db):
    row=correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,
        sentiment="POSITIVE",rationale="Original post tone was supportive."),user(db,1),db)
    assert row["paid_provider_called"] is False
    assert _latest_sentiment(db,70,200)=="Positive"
    assert _sentiment_details(db,70,200)["status"]=="OFFICER_CORRECTED"
    assert db.query(EvidenceAssessment).first().sentiment=="NEGATIVE"
    same=correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,
        sentiment="POSITIVE",rationale="Same classification as before."),user(db,1),db)
    assert same["unchanged"] is True
    changed=correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,
        sentiment="NEUTRAL",rationale="Closer assessment based on complete source."),user(db,1),db)
    assert changed["unchanged"] is False
    assert _latest_sentiment(db,70,200)=="Neutral"
    assert db.query(OfficerSentimentCorrection).count()==2

def test_viewer_and_wrong_region_cannot_correct(db):
    payload=CorrectionBody(campaign_id=70,result_id=200,sentiment="NEUTRAL",
        rationale="Documented reason from source.")
    for uid in (3,4):
        with pytest.raises(HTTPException) as e:
            correct_sentiment(payload,user(db,uid),db)
        assert e.value.status_code==403
    assert db.query(OfficerSentimentCorrection).count()==0

def test_sentiment_rejects_invalid_labels_and_allows_no_reason(db):
    with pytest.raises(HTTPException) as exc:
        correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,sentiment="WRONG",
            rationale="Unknown label should not be accepted."),user(db,1),db)
    assert exc.value.status_code==422
    assert db.query(OfficerSentimentCorrection).count()==0
    saved=correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,
        sentiment="NEUTRAL"),user(db,1),db)
    assert saved["unchanged"] is False
    assert saved["correction"]["rationale"]==""
    assert _latest_sentiment(db,70,200)=="Neutral"
    assert db.query(OfficerSentimentCorrection).count()==1
    assert db.query(EvidenceAssessment).first().sentiment=="NEGATIVE"

def test_pdf_retrieval_is_document_page_cited_and_permission_scoped(db):
    # Text fixture models the result of verified PDF extraction.
    pdf=KnowledgePDF(title="Peraturan Pengawasan Pemilu",filename="peraturan.pdf",
        scope="PROVINCE",province="Riau",content_sha256="a"*64,
        content_bytes=b"%PDF-synthetic-test",pages=2,extracted_chars=48,
        uploaded_by=1,active=True)
    db.add(pdf);db.flush()
    db.add(KnowledgeChunk(document_id=pdf.id,page=2,sequence=1,
                          text_content="Pengawasan pemilu memerlukan bukti dan pemeriksaan hukum oleh petugas."))
    db.commit()
    matches=retrieve_knowledge(db,p(db,2),"pengawasan pemilu dan bukti",limit=3)
    assert len(matches)==1
    assert matches[0]["record_id"]==f"DOC-{pdf.id}-P2"
    assert matches[0]["document_is_authority_unverified"] is True
    assert retrieve_knowledge(db,p(db,3),"pengawasan pemilu dan bukti")==[]
    assert _visible(p(db,1),pdf) and _visible(p(db,2),pdf)
    with pytest.raises(HTTPException) as error:
        download_pdf(pdf.id,user(db,3),db)
    assert error.value.status_code==404
    assert list_knowledge(user(db,3),db)["documents"]==[]

def test_pdf_upload_guard_rejects_image_only_scans_and_cross_province(db):
    writer=PdfWriter()
    writer.add_blank_page(width=595,height=842)
    stream=io.BytesIO();writer.write(stream)
    with pytest.raises(HTTPException) as error:
        _reader_pages(stream.getvalue())
    assert error.value.status_code==422
    with pytest.raises(HTTPException) as error:
        _allow_upload(p(db,2),"PROVINCE","Bali")
    assert error.value.status_code==403
    with pytest.raises(HTTPException) as error:
        _allow_upload(p(db,2),"NATIONAL","")
    assert error.value.status_code==403

def test_legal_review_never_equates_platform_policy_with_legal_verdict(monkeypatch,db):
    import app.campaigns as campaigns
    import app.assistant_knowledge as knowledge
    monkeypatch.setattr(campaigns,"campaign_action",lambda *args,**kwargs:{
        "findings":[{"id":"200","campaign_id":"70","platform":"instagram",
            "text_content":"Dugaan pelanggaran pemilu di Riau oleh pihak terkait.",
            "is_flagged":False,"potential_issues":[{"category":"Election"}],
            "flag_review_status":"UNREVIEWED","incident_jurisdiction_verified":False}]})
    monkeypatch.setattr(knowledge,"retrieve_knowledge",lambda *args,**kwargs:[])
    result=legal_snapshot(db,p(db,1))
    assert result["suspected_cases_in_sample"]==1
    assert result["legal_verdict"]=="NONE"
    assert result["platform_rule_verdict"]=="NONE"
    assert result["review_queue"][0]["legal_status"]=="REQUIRES_OFFICER_LEGAL_REVIEW"
    assert result["review_queue"][0]["platform_policy_status"]=="NOT_ASSESSED_AGAINST_CURRENT_PLATFORM_RULES"
    assert len(result["legal_follow_up_steps"])>=4


def test_hybrid_retrieval_finds_different_wording_and_keeps_page_citations(monkeypatch,db):
    import app.assistant_semantic as semantic
    doc=KnowledgePDF(title="Peraturan pengawasan",filename="rules.pdf",scope="PROVINCE",
        province="Riau",content_sha256="b"*64,content_bytes=b"%PDF-test",
        pages=2,extracted_chars=73,uploaded_by=1,active=True,
        document_type="REGULATION",issuer="Bawaslu",
        review_status="OFFICER_REVIEWED",embedding_status="READY",
        embedding_model=semantic.EMBED_MODEL)
    db.add(doc)
    db.flush()
    chunk=KnowledgeChunk(document_id=doc.id,page=2,sequence=1,
        text_content="Mekanisme tindak lanjut memerlukan pembuktian dan rapat pleno.")
    db.add(chunk)
    db.commit()
    # Query deliberately omits the wording used in the document. Fake the
    # vector match to test retrieval fusion, not the paid embedding service.
    monkeypatch.setattr(semantic,"semantic_search",
        lambda session,allowed_docs,question:[chunk])
    matches=retrieve_knowledge(db,p(db,2),"langkah tindakan untuk dugaan kesalahan",limit=4)
    assert len(matches)==1
    assert matches[0]["record_id"]==f"DOC-{doc.id}-P2"
    assert matches[0]["match_method"]=="SEMANTIC"
    assert matches[0]["review_status"]=="OFFICER_REVIEWED"
    assert matches[0]["legal_currentness_verified"] is False
    assert retrieve_knowledge(db,p(db,3),"langkah tindakan untuk dugaan kesalahan")==[]

def test_fusion_boosts_duplicate_keyword_and_semantic_match(db):
    from app.assistant_semantic import merge_rankings
    doc=KnowledgePDF(id=81,title="SOP penanganan pelanggaran",filename="sop.pdf",
        scope="NATIONAL",province="",content_sha256="c"*64,
        content_bytes=b"%PDF-fixture",pages=4,extracted_chars=40,uploaded_by=1,
        document_type="SOP",issuer="BAWASLU",review_status="UNREVIEWED")
    chunk=KnowledgeChunk(id=701,document_id=81,page=3,sequence=1,
        text_content="Penanganan pelanggaran memerlukan pemeriksaan saksi.")
    result=merge_rankings([chunk],[chunk],[doc],limit=4)
    assert len(result)==1
    assert result[0]["match_method"]=="HYBRID"
    assert result[0]["record_id"]=="DOC-81-P3"
    assert result[0]["legal_currentness_verified"] is False

def test_no_paid_semantic_call_without_indexed_documents(monkeypatch,db):
    import app.assistant_semantic as semantic
    def no_paid_calls(*args,**kwargs):
        raise AssertionError("Embeddings must not be called")
    monkeypatch.setattr(semantic,"embeddings",no_paid_calls)
    assert semantic.semantic_search(db,[],"pelanggaran pemilu")==[]
    matches=retrieve_knowledge(db,p(db,1),"pelanggaran pemilu",limit=6)
    assert matches==[]

def test_document_review_is_separate_from_legal_currentness(db):
    from app.assistant_knowledge import ReviewBody,review_pdf
    pdf=KnowledgePDF(title="Pedoman teknis",filename="pedoman.pdf",
       scope="PROVINCE",province="Riau",content_sha256="d"*64,
       content_bytes=b"%PDF-sample",pages=1,extracted_chars=40,uploaded_by=1,active=True)
    db.add(pdf)
    db.commit()
    reviewed=review_pdf(pdf.id,ReviewBody(document_type="SOP",
        issuer="Bawaslu Riau",notes="Checked original file and page integrity.",
        reviewed=True),user(db,1),db)
    assert reviewed["document"]["review_status"]=="OFFICER_REVIEWED"
    assert reviewed["legal_currentness_verified"] is False
    assert reviewed["document"]["issuer"]=="Bawaslu Riau"
    with pytest.raises(HTTPException) as ex:
        review_pdf(pdf.id,ReviewBody(document_type="SOP",notes="Checked again",
             reviewed=True),user(db,3),db)
    assert ex.value.status_code==404
    with pytest.raises(HTTPException) as ex:
        review_pdf(pdf.id,ReviewBody(document_type="SOP",notes="Checked again",
             reviewed=True),user(db,2),db)
    assert ex.value.status_code==403

def test_semantic_index_respects_explicit_opt_in_and_sqlite_fallback(db,monkeypatch):
    from app.assistant_semantic import index_document,embeddings,EMBED_DIMS
    pdf=KnowledgePDF(title="Sample",filename="sample.pdf",scope="NATIONAL",
        province="",content_sha256="e"*64,content_bytes=b"%PDF-sample",
        pages=1,extracted_chars=35,uploaded_by=1)
    chunk=KnowledgeChunk(document_id=1,page=1,sequence=1,
        text_content="Election regulations apply.")
    monkeypatch.setenv("OPENAI_API_KEY","fake-test-token")
    indexed,paid=index_document(db,pdf,[chunk])
    assert indexed is False and paid is False
    assert pdf.embedding_status=="UNSUPPORTED"
    # No external calls are made for tests; this checks the request shape and
    # validation contract with a local fake HTTP client.
    class Fake:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def post(self,url,headers,json):
            assert json["model"]=="text-embedding-3-small"
            assert len(json["input"])==1
            class Response:
                def raise_for_status(self):pass
                def json(self):
                    return {"data":[{"index":0,"embedding":[0.0]*EMBED_DIMS}]}
            return Response()
    monkeypatch.setattr("app.assistant_semantic.httpx.Client",lambda **kwargs:Fake())
    assert len(embeddings(["Election regulations apply."])[0])==EMBED_DIMS


def test_search_preview_does_not_generate_model_answer_and_is_scope_filtered(db):
    from app.assistant_knowledge import search_preview
    pdf=KnowledgePDF(title="SOP Pemeriksaan Pemilu",filename="sop.pdf",
        scope="PROVINCE",province="Riau",content_sha256="f"*64,
        content_bytes=b"%PDF-sample",pages=1,extracted_chars=50,
        uploaded_by=1,active=True)
    db.add(pdf);db.flush()
    db.add(KnowledgeChunk(document_id=pdf.id,page=1,sequence=1,
        text_content="Pemeriksaan pemilu harus berbasis bukti dan laporan petugas."))
    db.commit()
    result=search_preview("pemeriksaan pemilu",False,user(db,2),db)
    assert result["no_completion_call"] is True
    assert result["matches"][0]["record_id"]==f"DOC-{pdf.id}-P1"
    assert result["matches"][0]["match_method"]=="KEYWORD"
    assert search_preview("pemeriksaan pemilu",False,user(db,3),db)["matches"]==[]

def test_reason_is_optional_without_erasing_legacy_audit_history(db):
    first=correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,
        sentiment="POSITIVE",rationale="Earlier explanation retained in history."),user(db,1),db)
    second=correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,
        sentiment="NEUTRAL"),user(db,1),db)
    assert first["correction"]["rationale"]=="Earlier explanation retained in history."
    assert second["correction"]["rationale"]==""
    history=db.query(OfficerSentimentCorrection).order_by(OfficerSentimentCorrection.id).all()
    assert len(history)==2
    assert history[0].rationale=="Earlier explanation retained in history."
    assert history[1].rationale==""
    assert history[0].actor_id==history[1].actor_id==1
