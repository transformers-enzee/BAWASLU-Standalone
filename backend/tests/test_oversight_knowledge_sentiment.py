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


def test_platform_screening_political_criticism_is_not_a_policy_violation():
    from app.platform_policy_screening import screen_platform_text
    for platform in ("twitter","instagram","tiktok","youtube"):
        result=screen_platform_text(platform,
            "Gibran dinilai tidak memenuhi persyaratan pendidikan; PKS meminta DPR memeriksa putusan pengadilan.")
        assert result["status"]=="NO_DIRECT_SIGNAL_IDENTIFIED"
        assert result["review_categories"]==[]
        assert result["platform_violation_confirmed"] is False
        assert result["legal_violation_confirmed"] is False
        assert result["political_criticism_is_not_a_violation"] is True

def test_platform_screening_direct_threat_and_organized_abuse_cues():
    from app.platform_policy_screening import screen_platform_text
    threat=screen_platform_text("twitter-ai-search","Aku akan bunuh pejabat itu")
    assert threat["platform"]=="X"
    assert threat["status"]=="REVIEW_INDICATED"
    assert "DIRECT_THREAT" in threat["review_categories"]
    assert threat["policy_url"].startswith("https://help.x.com/")
    assert threat["platform_violation_confirmed"] is False
    doxx=screen_platform_text("tiktok","Sebarkan alamat rumah orang itu")
    assert doxx["status"]=="REVIEW_INDICATED"
    assert "PERSONAL_INFORMATION" in doxx["review_categories"]
    campaign=screen_platform_text("facebook","Ayo serbu akun mereka")
    assert campaign["status"]=="REVIEW_INDICATED"
    assert "COORDINATED_HARASSMENT" in campaign["review_categories"]

def test_platform_screening_news_quote_and_warning_are_contextual():
    from app.platform_policy_screening import screen_platform_text
    quoted=screen_platform_text("threads",
        "Berita: Polisi melaporkan seseorang berkata, 'Ayo serbu akun mereka'.")
    assert quoted["status"]=="CONTEXT_REVIEW_REQUIRED"
    assert quoted["context_required"] is True
    warning=screen_platform_text("youtube",
        "Jangan sebarkan alamat rumah seseorang, tindakan itu melanggar privasi.")
    assert warning["status"]=="CONTEXT_REVIEW_REQUIRED"
    assert warning["platform_violation_confirmed"] is False
    mention=screen_platform_text("instagram",
        "Berita pelanggaran pemilu dan tuduhan manipulasi persyaratan.")
    assert mention["review_categories"]==[]
    assert mention["status"]=="NO_DIRECT_SIGNAL_IDENTIFIED"

def test_platform_screening_unsupported_platform_does_not_claim_policy_review():
    from app.platform_policy_screening import screen_platform_text
    unknown=screen_platform_text("reddit","Ayo serbu akun mereka")
    assert unknown["status"]=="POLICY_NOT_CONFIGURED"
    assert unknown["policy_url"] is None
    assert unknown["platform_violation_confirmed"] is False
    assert screen_platform_text("tiktok","")["status"]=="INSUFFICIENT_SOURCE"

def test_platform_screening_queue_is_independent_of_legal_queue(monkeypatch,db):
    import app.campaigns as campaigns
    import app.assistant_knowledge as knowledge
    monkeypatch.setattr(campaigns,"campaign_action",lambda *args,**kwargs:{
        "findings":[
            {"id":"201","campaign_id":"70","platform":"threads",
             "text_content":"Ayo serbu akun mereka","is_flagged":False,
             "potential_issues":[],"flag_review_status":"UNREVIEWED"},
            {"id":"202","campaign_id":"70","platform":"twitter",
             "text_content":"Berita menyebut: ayo serbu akun mereka.",
             "is_flagged":False,"potential_issues":[]},
            {"id":"203","campaign_id":"70","platform":"twitter",
             "text_content":"Berita kritis tentang Gibran dan proses pemilu.",
             "is_flagged":True,"potential_issues":[{"category":"LEGAL_REVIEW"}]},
            {"id":"204","campaign_id":"70","platform":"reddit",
             "text_content":"Ayo serbu akun mereka","is_flagged":False,
             "potential_issues":[]},
        ]})
    monkeypatch.setattr(knowledge,"retrieve_knowledge",lambda *args,**kwargs:[])
    snapshot=legal_snapshot(db,p(db,1))
    legal_ids={item["source_id"] for item in snapshot["review_queue"]}
    assert legal_ids=={"203"}
    screened=snapshot["platform_policy_screening"]
    assert screened["screened_posts_in_sample"]==3
    assert screened["review_signal_count_in_sample"]==1
    assert screened["reported_or_contextual_count_in_sample"]==1
    assert [item["source_id"] for item in screened["review_queue"]]==["201","202"]
    assert all(item["platform_violation_confirmed"] is False for item in screened["review_queue"])
    assert snapshot["legal_verdict"]=="NONE"
    assert snapshot["platform_rule_verdict"]=="NONE"
    assert snapshot["paid_provider_called"] is False


def _chat_pdf_fixture(db,province="Riau",scope="PROVINCE",digest="7"):
    pdf=KnowledgePDF(title="Contoh rujukan simulasi BAWASLU",
        filename="contoh-konteks.pdf",scope=scope,
        province=province if scope=="PROVINCE" else "",
        content_sha256=digest*64,content_bytes=b"%PDF-synthetic",
        pages=8,extracted_chars=1000,uploaded_by=1,
        document_type="GUIDANCE",review_status="UNREVIEWED",active=True)
    db.add(pdf);db.flush()
    chunks=[
        (1,"Daftar isi simulasi dan informasi umum."),
        (3,"Panduan pengamanan dan registrasi informasi awal dalam berkas."),
        (6,"Tindak lanjut pengamanan bukti digital perlu pemeriksaan petugas."),
        (8,"Penugasan provinsi hanya setelah lokasi kejadian diverifikasi oleh petugas."),
    ]
    for page,body in chunks:
        db.add(KnowledgeChunk(document_id=pdf.id,page=page,sequence=page,
                              text_content=body))
    db.commit()
    return pdf


def test_chat_pdf_context_survives_followup_and_stays_permission_scoped(db,monkeypatch):
    from app.assistant_knowledge import (
        retrieve_chat_knowledge,authorized_reference_catalog)
    from app import assistant_semantic
    def paid_embedding_would_be_wrong(*args,**kwargs):
        raise AssertionError("Do not call embeddings without an indexed PDF.")
    monkeypatch.setattr(assistant_semantic,"embeddings",paid_embedding_would_be_wrong)
    pdf=_chat_pdf_fixture(db)
    question="Jelaskan proses tindak lanjut pengamanan bukti digital"
    initial=retrieve_chat_knowledge(db,p(db,2),question,limit=4)
    assert f"DOC-{pdf.id}-P6" in [x["record_id"] for x in initial]
    assert all(x["document_id"]==pdf.id for x in initial)
    next_turn=retrieve_chat_knowledge(db,p(db,2),"Bagaimana dengan provinsi?",
        previous=question,history=[
            {"role":"user","text":question},
            {"role":"assistant","text":"Pemeriksaan bukti perlu dilakukan."}],limit=6)
    ids=[x["record_id"] for x in next_turn]
    assert f"DOC-{pdf.id}-P8" in ids
    assert f"DOC-{pdf.id}-P6" in ids
    assert len(ids)==len(set(ids))
    assert all(x["legal_currentness_verified"] is False for x in next_turn)
    assert retrieve_chat_knowledge(db,p(db,3),"Bagaimana dengan provinsi?",
        previous=question)==[]
    assert authorized_reference_catalog(db,p(db,3))==[]
    assert authorized_reference_catalog(db,p(db,2))[0]["id"]==pdf.id


def test_chat_pdf_broad_summary_uses_page_spread_with_no_paid_calls(db,monkeypatch):
    from app.assistant_knowledge import retrieve_chat_knowledge
    from app import assistant_semantic
    monkeypatch.setattr(assistant_semantic,"embeddings",lambda *_args,**_kwargs:
        (_ for _ in ()).throw(AssertionError("No embedding calls expected")))
    pdf=_chat_pdf_fixture(db,scope="NATIONAL",digest="8")
    pages=retrieve_chat_knowledge(db,p(db,1),"Please summarize the attached PDF",limit=6)
    assert [item["page"] for item in pages]==[1,3,6,8]
    assert all(item["document_id"]==pdf.id for item in pages)
    assert all(item["match_method"]=="DOCUMENT_OVERVIEW" for item in pages)
    assert retrieve_chat_knowledge(db,p(db,1),"",limit=6)==[]


def test_normal_assistant_chat_automatically_includes_pdf_and_references(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import assistant_orchestration,domain,campaigns
    _chat_pdf_fixture(db,scope="NATIONAL",digest="9")
    monkeypatch.setattr(domain,"list_intelligence",lambda *_:[])
    monkeypatch.setattr(campaigns,"campaign_action",
        lambda *_args,**_kwargs:{"findings":[]})
    seen={}
    def fake_generate(question,previous,evidence,mode,**kwargs):
        seen["evidence"]=evidence
        seen["catalog"]=kwargs["reference_catalog"]
        seen["history"]=kwargs["history"]
        cited=next(x["record_id"] for x in evidence
                   if x["record_type"]=="PDF_KNOWLEDGE" and x["page"]==6)
        return "Rujukan halaman 6: "+cited,[cited],{
            "answer_language":"id","detected_tags":[],
            "presentation_labels":[]}
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    result=intelligence_assistant({
        "question":"Jelaskan proses tindak lanjut pengamanan bukti digital",
        "previousQuestion":"",
        "analysisMode":"AUTO","responseDepth":"DEEP",
        "conversationContext":[{"role":"user","text":"Saya ingin memahami SOP PDF."}]},
        user(db,1),db)
    assert result["records"][0]["record_type"]=="PDF_KNOWLEDGE"
    assert result["records"][0]["page"]==6
    assert result["records"][0]["record_id"].startswith("DOC-")
    assert result["grounding"]["automatic_pdf_context"] is True
    assert result["grounding"]["reference_pdf_count"]==1
    assert result["grounding"]["reference_page_count"]>=1
    assert seen["catalog"][0]["review_status"]=="UNREVIEWED"
    assert seen["history"][-1]["role"]=="user"


@pytest.mark.parametrize("question,previous,has_pdf,expected",[
    ("Menurut PDF BAWASLU yang telah diunggah, apa langkah tindak lanjut hukum setelah takedown?",
     "",True,"PDF_GUIDANCE"),
    ("Bagaimana dengan penugasan ke tim provinsi?",
     "Menurut PDF BAWASLU, apa langkah tindak lanjut hukum setelah takedown?",True,"PDF_GUIDANCE"),
    ("Jelaskan alur verifikasi yurisdiksi dan kewenangan petugas",
     "",True,"PDF_GUIDANCE"),
    ("Apa tren sentimen dan narasi dari unggahan terbaru?",
     "Sebutkan SOP dari PDF",True,"SOCIAL_ANALYSIS"),
    ("Analisis sentimen dan engagement dari 100 unggahan",
     "",False,"SOCIAL_ANALYSIS"),
    ("Investigasi dugaan pelanggaran Gibran berdasarkan Intelligence Inbox dan Social Listening",
     "",True,"CASE_REVIEW"),
    ("Investigasi kasus #739 dan periksa bukti primer",
     "",True,"CASE_REVIEW"),
    ("Buatkan laporan dari temuan tersimpan",
     "",True,"ACTION_REQUEST"),
    ("Siapkan penugasan untuk menindaklanjuti temuan",
     "",True,"ACTION_REQUEST"),
    ("Susun draf laporan berdasarkan bukti sumber",
     "",True,"ACTION_REQUEST"),
    ("How does the law treat this?",
     "",False,"SOCIAL_ANALYSIS"),
])
def test_assistant_response_profile_routing(question,previous,has_pdf,expected):
    from app.assistant_response_profile import choose_response_profile
    snippets=[{"record_id":"DOC-1-P8"}] if has_pdf else []
    assert choose_response_profile(question,previous,snippets)==expected


def test_pdf_guidance_chat_uses_only_pdf_skips_social_stats_and_action_cards(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import assistant_orchestration,domain,campaigns
    _chat_pdf_fixture(db,scope="NATIONAL",digest="6")
    def must_not_read_social(*_args,**_kwargs):
        raise AssertionError("PDF-only request must not load the social Inbox")
    monkeypatch.setattr(domain,"list_intelligence",must_not_read_social)
    monkeypatch.setattr(campaigns,"campaign_action",must_not_read_social)
    observed={}
    def fake_generate(question,previous,evidence,mode,**kwargs):
        observed["profile"]=kwargs.get("response_profile")
        observed["evidence"]=evidence
        assert mode=="GROUNDED"
        assert kwargs["response_depth"]=="EXECUTIVE"
        cited=next(row["record_id"] for row in evidence if row["page"]==6)
        return "Menurut PDF, amankan bukti digital "+f"[{cited}]",[cited],{
            "answer_language":"id",
            "detected_tags":[{"type":"CANDIDATE","label":"Unrelated"}],
            "analytical_findings":{"observations":["Wrong source"]},
            "presentation_labels":[]}
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    output=intelligence_assistant({
        "question":"Menurut PDF, jelaskan tindak lanjut pengamanan bukti digital",
        "previousQuestion":"","analysisMode":"AUTO",
        "responseDepth":"DEEP","conversationContext":[]},user(db,1),db)
    assert output["response_profile"]=="PDF_GUIDANCE"
    assert observed["profile"]=="PDF_GUIDANCE"
    assert all(row["record_type"]=="PDF_KNOWLEDGE" for row in observed["evidence"])
    assert [row["page"] for row in output["records"]]==[6]
    assert output["detected_tags"]==[]
    assert output["evidence_snapshot"] is None
    assert output["featured_sources"]==[]
    assert output["analytical_findings"] is None
    assert output["grounding"]["scope"]=="AUTHORIZED_PDF_REFERENCES"


def test_followup_question_uses_pdf_page_without_unrelated_intelligence(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import assistant_orchestration,domain,campaigns
    _chat_pdf_fixture(db,scope="NATIONAL",digest="5")
    monkeypatch.setattr(domain,"list_intelligence",
                        lambda *_:(_ for _ in ()).throw(AssertionError("Social feed called")))
    monkeypatch.setattr(campaigns,"campaign_action",
                        lambda *_args,**_kwargs:(_ for _ in ()).throw(AssertionError("Campaign called")))
    def fake_generate(question,previous,evidence,mode,**kwargs):
        citations=[row["record_id"] for row in evidence if row["page"]==8]
        assert citations
        return "Penugasan memerlukan verifikasi yurisdiksi ["+citations[0]+"]",citations,{
            "answer_language":"id","detected_tags":[],"presentation_labels":[]}
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    result=intelligence_assistant({
        "question":"Bagaimana dengan penugasan ke tim provinsi?",
        "previousQuestion":"Menurut PDF, jelaskan tindak lanjut pengamanan bukti digital",
        "analysisMode":"AUTO","responseDepth":"DEEP",
        "conversationContext":[{"role":"user","text":"Menurut PDF, jelaskan tindak lanjut pengamanan bukti digital"}]},
        user(db,1),db)
    assert result["response_profile"]=="PDF_GUIDANCE"
    assert result["records"][0]["page"]==8
    assert not result["featured_sources"]


def test_saved_conversation_remembers_simplified_answer_profile():
    from app.assistant_history import clean_messages
    snapshot=clean_messages([
        {"role":"user","text":"Menurut PDF, bagaimana penugasan provinsi?"},
        {"role":"assistant","text":"Locus harus dikonfirmasi [DOC-1-P8].",
         "response_profile":"PDF_GUIDANCE","records":[]},
    ])
    assert snapshot[1]["response_profile"]=="PDF_GUIDANCE"
    assert clean_messages([{"role":"assistant","text":"Other",
                           "response_profile":"FAKE_MODE"}])[0]["response_profile"]==""


def test_social_tags_focus_on_requested_candidate_without_unrequested_province():
    from app.assistant_social_focus import focus_social_tags,query_candidates
    q="Analisis sentimen publik terhadap Gibran Rakabuming Raka dari Social Listening"
    assert "gibran rakabuming raka" in query_candidates(q)
    tags=[
        {"type":"CANDIDATE","label":"Denny Indrayana","source_ids":["SOCIAL-1"],"confidence":"HIGH"},
        {"type":"CANDIDATE","label":"Gibran Rakabuming Raka","source_ids":["SOCIAL-1"],"confidence":"HIGH"},
        {"type":"PROVINCE","label":"Sumatera Utara","source_ids":["SOCIAL-1"],"confidence":"HIGH"},
        {"type":"SUSPECTED_VIOLATION","label":"Dugaan dokumen pendidikan","source_ids":["SOCIAL-1"],"confidence":"MEDIUM"},
        {"type":"BAWASLU_ISSUE","label":"Transparansi pengawasan","source_ids":["SOCIAL-2"],"confidence":"MEDIUM"},
        {"type":"ELECTORAL_ISSUE","label":"Electoral operations","source_ids":["SOCIAL-1"],"confidence":"HIGH"},
        {"type":"BAWASLU_ISSUE","label":"Unlinked tag","source_ids":["SOCIAL-999"],"confidence":"HIGH"}
    ]
    actual=focus_social_tags(tags,q,["SOCIAL-1","SOCIAL-2"])
    assert [x["label"] for x in actual]==["Gibran Rakabuming Raka","Transparansi pengawasan"]
    assert all(set(x["source_ids"]) <= {"SOCIAL-1","SOCIAL-2"} for x in actual)


def test_social_metrics_use_exact_ai_sample_not_larger_result_pool(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import assistant_orchestration,domain,campaigns
    monkeypatch.setattr(domain,"list_intelligence",lambda *_:[])
    def source(pid,text,sentiment,engagement=0,relevance="RELEVANT"):
        return {"id":pid,"campaign_id":70,"campaign_name":"Gibran pencalonan",
                "platform":"instagram","author_name":"test-source",
                "text_content":text,"relevance_label":relevance,
                "sentiment":sentiment,"published_at":"2026-11-02",
                "engagement_total":engagement}
    rows=[
        source(501,"Gibran Rakabuming Raka membahas dokumen pendidikan KPU.","NEUTRAL",2),
        source(502,"Sengketa ijazah Gibran Rakabuming Raka di KPU.","NEGATIVE",8),
        source(503,"Isu lain yang tidak terkait dengan kandidat.","POSITIVE",888888),
        source(504,"Gibran Rakabuming Raka video lama.","NEGATIVE",999999,"IRRELEVANT"),
    ]
    rows[2]["campaign_name"]="Other campaign"
    monkeypatch.setattr(campaigns,"campaign_action",lambda *_a,**_kw:{"findings":rows})
    def fake_generate(q,previous,evidence,mode,**kwargs):
        assert len([x for x in evidence if x.get("record_type")=="SOCIAL_LISTENING"])==2
        return ("Dua unggahan: satu netral dan satu negatif [SOCIAL-501] [SOCIAL-502].",
                ["SOCIAL-501","SOCIAL-502"],
                {"answer_language":"id","presentation_labels":{},
                 "detected_tags":[
                     {"type":"CANDIDATE","label":"Gibran Rakabuming Raka",
                      "source_ids":["SOCIAL-501"],"confidence":"HIGH"},
                     {"type":"CANDIDATE","label":"Denny Indrayana",
                      "source_ids":["SOCIAL-502"],"confidence":"HIGH"},
                     {"type":"PROVINCE","label":"Sumatera Utara",
                      "source_ids":["SOCIAL-501"],"confidence":"MEDIUM"}]})
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    result=intelligence_assistant({
        "question":"Analisis sentimen publik terhadap Gibran Rakabuming Raka",
        "previousQuestion":"","analysisMode":"AUTO","responseDepth":"DEEP",
        "conversationContext":[]},user(db,1),db)
    snap=result["evidence_snapshot"]
    assert result["response_profile"]=="SOCIAL_ANALYSIS"
    assert snap["statistics_scope"]=="SAME_SELECTED_POSTS_AS_AI_ANALYSIS"
    assert snap["social_posts"]==snap["analysis_post_count"]==snap["statistics_post_count"]==2
    assert snap["sentiment_counts"]["NEUTRAL"]==1
    assert snap["sentiment_counts"]["NEGATIVE"]==1
    assert sum(snap["sentiment_counts"].values())==2
    assert snap["observed_engagement"]==10
    assert {x["source_post_id"] for x in result["featured_sources"]}=={"501","502"}
    assert [x["label"] for x in result["detected_tags"]]==["Gibran Rakabuming Raka"]


def test_social_cards_only_use_analyzed_sources():
    from app.assistant_social_focus import source_cards_for_question
    rows=[{"id":1},{"id":2},{"id":3}]
    cards=source_cards_for_question(rows,["SOCIAL-3"],lambda r:{"id":r["id"]},limit=2)
    assert [x["id"] for x in cards]==[3,1]


def test_procedural_pdf_question_without_word_pdf_still_uses_reference():
    from app.assistant_response_profile import choose_response_profile
    q="Jelaskan proses tindak lanjut pengamanan bukti digital"
    assert choose_response_profile(q,pdf_evidence=[{"record_id":"DOC-1-P6"}])=="PDF_GUIDANCE"


def test_case_investigation_with_social_listening_routes_to_review_without_charts(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import assistant_orchestration,domain,campaigns
    monkeypatch.setattr(domain,"list_intelligence",lambda *_:[])
    monkeypatch.setattr(campaigns,"campaign_action",lambda *_args,**_kwargs:{
        "findings":[{"id":9901,"campaign_name":"bawaslu","platform":"instagram",
                     "author_name":"newsroom","text_content":"Gibran Rakabuming Raka dilaporkan terkait verifikasi dokumen pendidikan",
                     "relevance_label":"RELEVANT","sentiment":"NEUTRAL",
                     "published_at":"2026-11-02","engagement_total":3}]})
    def fake_generate(question,previous,evidence,mode,**kwargs):
        assert kwargs["response_profile"]=="CASE_REVIEW"
        return ("Klaim perlu diverifikasi [SOCIAL-9901]",["SOCIAL-9901"],{
            "answer_language":"id","detected_tags":[],
            "analytical_findings":{"observations":["Perlu dokumen resmi [SOCIAL-9901]"],
                                   "review_steps":["Periksa arsip otoritatif [SOCIAL-9901]"]}})
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    result=intelligence_assistant({
        "question":"Investigasi dugaan pelanggaran Gibran Rakabuming Raka berdasarkan Intelligence Inbox dan Social Listening",
        "previousQuestion":"","analysisMode":"AUTO","responseDepth":"DEEP",
        "conversationContext":[]},user(db,1),db)
    assert result["response_profile"]=="CASE_REVIEW"
    assert result["evidence_snapshot"] is None
    assert result["grounding"]["formal_selected_count"]==0
    assert result["grounding"]["social_selected_count"]==1
    assert result["analytical_findings"]["review_steps"]



def test_case_source_cards_prioritize_distinct_evidence_over_platform_reposts():
    from app.assistant_social_focus import source_cards_for_question
    rows=[
        {"id":205,"text_content":"Sindonews melaporkan pemeriksaan dokumen pendidikan dan proses pencalonan yang menjadi sorotan media sosial."},
        {"id":155,"text_content":"Sindonews melaporkan pemeriksaan dokumen pendidikan dan proses pencalonan yang menjadi sorotan media sosial."},
        {"id":179,"text_content":"Bawaslu menyampaikan adanya klaim mengenai keterbatasan akses Silon dalam proses pengawasan pencalonan."},
        {"id":740,"text_content":"Media menyoroti perlunya verifikasi status putusan resmi lembaga peradilan sebelum menyimpulkan implikasi hukum."},
    ]
    cards=source_cards_for_question(rows,["SOCIAL-205","SOCIAL-155","SOCIAL-179"],
                                  lambda row:{"id":row["id"]},limit=3,distinct_content=True)
    assert [row["id"] for row in cards]==[205,179,740]


def test_case_reference_filter_retains_procedure_not_unrelated_simulation_training():
    from app.assistant_response_profile import select_case_reference_pages
    pages=[
        {"record_id":"DOC-1-P6","record_type":"PDF_KNOWLEDGE",
         "source_excerpt":"Tindak lanjut dugaan pelanggaran: amankan bukti dan periksa kewenangan."},
        {"record_id":"DOC-1-P10","record_type":"PDF_KNOWLEDGE",
         "source_excerpt":"Kasus simulasi BWS-RAG-042: Skenario ini sepenuhnya fiktif."},
        {"record_id":"DOC-1-P12","record_type":"PDF_KNOWLEDGE",
         "source_excerpt":"Pertanyaan uji dan kriteria lulus untuk evaluasi AI."},
    ]
    question="Investigasi persyaratan pendidikan Gibran dari Social Listening"
    assert [r["record_id"] for r in select_case_reference_pages(question,pages)]==["DOC-1-P6"]
    explicit=select_case_reference_pages("Investigasi kasus simulasi BWS-RAG-042",pages)
    assert {r["record_id"] for r in explicit}=={"DOC-1-P6","DOC-1-P10","DOC-1-P12"}



def test_cross_module_comparison_routing_preserves_explicit_sentiment_requests():
    from app.assistant_response_profile import choose_response_profile,CROSS_MODULE_REVIEW,SOCIAL_ANALYSIS
    q=("Bandingkan informasi yang tersimpan di Intelligence Inbox dan Social Listening "
       "mengenai akses Bawaslu terhadap Silon KPU serta Gibran Rakabuming Raka.")
    assert choose_response_profile(q)==CROSS_MODULE_REVIEW
    assert choose_response_profile("Analisis sentimen Gibran dari Social Listening")==SOCIAL_ANALYSIS


def test_cross_module_focus_excludes_unrelated_approved_inbox_items():
    from types import SimpleNamespace
    from app.assistant_response_profile import cross_module_formal_focus
    question=("Bandingkan Intelligence Inbox dan Social Listening mengenai "
              "akses Silon dan pendidikan Gibran Rakabuming Raka")
    rows=[
        SimpleNamespace(intelligence_id="INT-2026-000001",
                        title="Muhammad Bobby Afif Nasution",
                        original_content="Biografi gubernur Sumatera Utara",source_name=""),
        SimpleNamespace(intelligence_id="INT-2026-000004",
                        title="ibarat globe berjalan #debat #bawaslu",
                        original_content="debate activity",source_name=""),
        SimpleNamespace(intelligence_id="INT-2026-000099",
                        title="Dokumen akses Silon dalam kasus pendidikan",
                        original_content="Verifikasi persyaratan Gibran",source_name=""),
    ]
    selected=cross_module_formal_focus(question,rows)
    assert [r.intelligence_id for r in selected]==["INT-2026-000099"]
    assert cross_module_formal_focus(question,rows[:2])==[]
    assert cross_module_formal_focus("Bandingkan kedua modul",rows)==rows


def test_cross_module_duplicate_groups_and_featured_cards_are_distinct():
    from app.assistant_social_focus import potential_duplicate_groups,source_cards_for_question
    common=("Dalam cuplikan video diskusi ini, narasumber menyoroti persoalan "
            "krusial terkait minimnya akses pengawasan Bawaslu dalam melakukan "
            "verifikasi dokumen serta kredensial pendidikan Gibran.")
    rows=[{"id":179,"text_content":common+" Pertanyaan lanjutan tentang KPU."},
          {"id":184,"text_content":common+" Pertanyaan lanjutan tentang KPU"},
          {"id":205,"text_content":"Pemeriksaan dokumen pendidikan Gibran secara resmi dibahas pada rapat komisi pemilihan umum."}]
    groups=potential_duplicate_groups(rows)
    assert groups and set(groups[0]["source_ids"])=={"SOCIAL-179","SOCIAL-184"}
    cards=source_cards_for_question(rows,["SOCIAL-179","SOCIAL-184"],lambda r:{"id":r["id"]},
                                    limit=4,distinct_content=True)
    assert [r["id"] for r in cards]==[179,205]


def test_cross_module_endpoint_discloses_missing_inbox_and_skips_sentiment_charts(monkeypatch,db):
    from app import domain,campaigns,assistant_orchestration
    from app.main import intelligence_assistant
    monkeypatch.setattr(domain,"list_intelligence",lambda *_:[])
    monkeypatch.setattr(campaigns,"campaign_action",lambda *_args,**_kwargs:{
        "findings":[{"id":9901,"campaign_name":"bawaslu","platform":"tiktok",
                     "text_content":"Bawaslu membahas akses Silon KPU terkait pendidikan Gibran Rakabuming Raka",
                     "relevance_label":"RELEVANT","sentiment":"NEUTRAL"}]})
    def fake_generate(question,previous,evidence,mode,**kwargs):
        assert kwargs["response_profile"]=="CROSS_MODULE_REVIEW"
        assert all(row["record_type"]=="SOCIAL_LISTENING" for row in evidence)
        return ("Tidak ditemukan Inbox relevan. Klaim belum terverifikasi [SOCIAL-9901]",
                ["SOCIAL-9901"],{"answer_language":"id","detected_tags":[],
                    "analytical_findings":{"observations":["Klaim akses Silon [SOCIAL-9901]"],
                                          "review_steps":["Periksa dokumen KPU"]}})
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    result=intelligence_assistant({
        "question":"Bandingkan Intelligence Inbox dan Social Listening terkait akses Silon KPU dan pendidikan Gibran Rakabuming Raka",
        "previousQuestion":"","analysisMode":"AUTO","responseDepth":"DEEP",
        "conversationContext":[]},user(db,1),db)
    assert result["response_profile"]=="CROSS_MODULE_REVIEW"
    assert result["evidence_snapshot"] is None
    assert result["grounding"]["formal_selected_count"]==0
    assert result["grounding"]["social_selected_count"]==1
    assert all(row["record_type"]=="SOCIAL_LISTENING" for row in result["records"])
    assert result["featured_sources"][0]["id"]=="SOCIAL-9901"



def test_test4_pdf_only_request_ignores_negated_social_modules(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import assistant_orchestration,domain,campaigns
    document=_chat_pdf_fixture(db,scope="NATIONAL",digest="8")
    from app import assistant_knowledge
    # The fixture has a short excerpt. Mock the authorized retrieval result so
    # this test isolates endpoint routing, rather than lexical ranking.
    page6={
        "record_id":f"DOC-{document.id}-P6","record_type":"PDF_KNOWLEDGE",
        "document_id":document.id,"title":document.title,"filename":document.filename,
        "page":6,"source_excerpt":"Tindak lanjut dugaan pelanggaran hukum: amankan bukti digital.",
        "verification_status":"UPLOADED_DOCUMENT_NOT_LEGAL_VALIDATION"
    }
    monkeypatch.setattr(assistant_knowledge,"retrieve_chat_knowledge",
                        lambda *_args,**_kwargs:[page6])
    prompt=(
        "Berdasarkan dokumen PDF BAWASLU_Sample_AI_Knowledge_Full_Text yang tersimpan "
        "dalam AI Reference Library, jelaskan langkah-langkah penanganan awal "
        "informasi dugaan pelanggaran pemilu. Bedakan secara jelas antara proses "
        "penanganan dugaan pelanggaran hukum dan moderasi konten berdasarkan "
        "kebijakan platform media sosial. Gunakan hanya informasi yang benar-benar "
        "tersedia dalam PDF, sertakan sitasi halaman yang tepat, dan jelaskan "
        "status dokumen tersebut apakah merupakan simulasi atau SOP resmi Bawaslu. "
        "Jangan menggunakan sumber Social Listening atau Intelligence Inbox "
        "untuk menjawab pertanyaan ini. Jangan mengarang ketentuan hukum, "
        "nomor pasal, atau prosedur yang tidak tersedia dalam dokumen. "
        "Jika informasi tidak tersedia, nyatakan secara eksplisit."
    )
    assert len(prompt)<=1000
    from app.assistant_response_profile import choose_response_profile
    assert choose_response_profile(prompt,pdf_evidence=[{"record_id":"DOC-1-P6"}])=="PDF_GUIDANCE"
    def forbidden(*args,**kwargs):
        raise AssertionError("PDF-only Test 4 must not query Social Listening or Inbox")
    monkeypatch.setattr(domain,"list_intelligence",forbidden)
    monkeypatch.setattr(campaigns,"campaign_action",forbidden)
    seen={}
    def fake_generate(question,previous,evidence,mode,**kwargs):
        seen["profile"]=kwargs["response_profile"]
        assert mode=="GROUNDED"
        assert evidence and all(row["record_type"]=="PDF_KNOWLEDGE" for row in evidence)
        rid=next(row["record_id"] for row in evidence if row["page"]==6)
        return "Dokumen simulasi, bukan SOP resmi ["+rid+"]",[rid],{
            "answer_language":"id","detected_tags":[{"type":"CANDIDATE","label":"Gibran"}],
            "analytical_findings":{"observations":["irrelevant finding"]}}
    monkeypatch.setattr(assistant_orchestration,"generate",fake_generate)
    response=intelligence_assistant({"question":prompt,"previousQuestion":"",
        "analysisMode":"AUTO","responseDepth":"DEEP","conversationContext":[]},
        user(db,1),db)
    assert seen["profile"]=="PDF_GUIDANCE"
    assert response["response_profile"]=="PDF_GUIDANCE"
    assert response["evidence_snapshot"] is None
    assert response["analytical_findings"] is None
    assert response["detected_tags"]==[]
    assert response["featured_sources"]==[]
    assert response["records"] and all(r["record_type"]=="PDF_KNOWLEDGE"
                                       for r in response["records"])
    assert response["grounding"]["formal_selected_count"]==0
    assert response["grounding"]["social_selected_count"]==0


def test_explicit_pdf_only_without_available_pages_does_not_hallucinate(monkeypatch,db):
    from app.main import intelligence_assistant
    from app import domain,campaigns
    from app import assistant_knowledge
    monkeypatch.setattr(assistant_knowledge,"retrieve_chat_knowledge",lambda *_a,**_k:[])
    monkeypatch.setattr(domain,"list_intelligence",
                        lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("Inbox read")))
    monkeypatch.setattr(campaigns,"campaign_action",
                        lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("Social read")))
    result=intelligence_assistant({"question":"Berdasarkan dokumen PDF, jelaskan aturan.",
        "previousQuestion":"","analysisMode":"AUTO","responseDepth":"DEEP",
        "conversationContext":[]},user(db,1),db)
    assert result["response_profile"]=="PDF_GUIDANCE"
    assert result["records"]==[]
    assert result["provider"]["mode"]=="NO_PDF_EVIDENCE"
    assert result["grounding"]["scope"]=="AUTHORIZED_PDF_REFERENCES"
