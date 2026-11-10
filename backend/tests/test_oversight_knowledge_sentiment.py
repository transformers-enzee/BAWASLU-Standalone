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

def test_sentiment_rejects_invalid_labels_and_short_reasons(db):
    with pytest.raises(HTTPException) as exc:
        correct_sentiment(CorrectionBody(campaign_id=70,result_id=200,sentiment="WRONG",
            rationale="Unknown label should not be accepted."),user(db,1),db)
    assert exc.value.status_code==422
    assert db.query(OfficerSentimentCorrection).count()==0

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
    import app.oversight_legal as legal
    monkeypatch.setattr(campaigns,"campaign_action",lambda *args,**kwargs:{
        "findings":[{"id":"200","campaign_id":"70","platform":"instagram",
            "text_content":"Dugaan pelanggaran pemilu di Riau oleh pihak terkait.",
            "is_flagged":False,"potential_issues":[{"category":"Election"}],
            "flag_review_status":"UNREVIEWED","incident_jurisdiction_verified":False}]})
    monkeypatch.setattr(legal,"retrieve_knowledge",lambda *args,**kwargs:[])
    result=legal_snapshot(db,p(db,1))
    assert result["suspected_cases_in_sample"]==1
    assert result["legal_verdict"]=="NONE"
    assert result["platform_rule_verdict"]=="NONE"
    assert result["review_queue"][0]["legal_status"]=="REQUIRES_OFFICER_LEGAL_REVIEW"
    assert result["review_queue"][0]["platform_policy_status"]=="NOT_ASSESSED_AGAINST_CURRENT_PLATFORM_RULES"
    assert len(result["legal_follow_up_steps"])>=4
