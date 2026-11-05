"""Casework routing, AI-tag hints and report approvals: no external AI calls."""
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (User,AccessGrant,MonitoringCampaign,SocialListeningResult,
    CampaignEvidence,EvidenceAssessment,CampaignJurisdictionReview)
from app.access import default_permissions, profile
from app.jurisdiction_review import fingerprint
from app.casework import (_source,_visible,_validate_route,CaseAssignment,CaseReport,
    AssistantHandoff,assistant_handoff,assistant_workspace,CaseTransition,
    NewCase,ReportDraft,ReportAction,create_case,create_report,transition_report)

def dataset():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db=Session(engine)
    for uid,name,role,scope,province in [
        (1,"national","National Administrator","Nationwide",""),
        (2,"riau","Provincial Analyst","Province","Riau"),
        (3,"bali","Provincial Analyst","Province","Bali"),
        (4,"review","National Administrator","Nationwide","")
    ]:
        db.add(User(id=uid,email=name+"@test.invalid",full_name=name,password_hash="unused"))
        db.add(AccessGrant(user_id=uid,access_role=role,geographic_scope=scope,
            province=province,status="Active",permissions_json=json.dumps(default_permissions(role))))
    db.add(MonitoringCampaign(id=90,name="Election signals in Riau",province="Riau",
        created_by="1",primary_keywords_json='["pemilu"]'))
    text="Dugaan pelanggaran di Riau: BAWASLU memeriksa informasi pencalonan Gibran dalam pemilu."
    db.add(SocialListeningResult(id=11,run_id=2,platform="instagram",
        text_content=text,canonical_url="https://example.test/post/11",published_at="2026-11-05"))
    db.add(CampaignEvidence(campaign_id=90,result_id=11))
    db.add(EvidenceAssessment(campaign_id=90,result_id=11,assessment_version=1,
        relevance_label="RELEVANT",
        candidate_signals_json='["Gibran Rakabuming Raka"]',
        potential_issue_signals_json='[{"category":"Election Process","evidence_quote":"Dugaan pelanggaran di Riau"}]',
        topic_labels_json='["Electoral Operations","BAWASLU Reputation"]'))
    db.commit()
    return db

def p(db,uid):
    return profile(db,db.get(User,uid))

def confirmed(db):
    source=db.get(SocialListeningResult,11)
    db.add(CampaignJurisdictionReview(campaign_id=90,result_id=11,province="Riau",
        evidence_fingerprint=fingerprint(source.text_content),
        decision="CONFIRMED",rationale="Source location checked against original text.",
        reviewer_id="1"))
    db.commit()

def test_preview_detects_saved_candidate_region_issues_and_violation_hint_without_granting_access():
    db=dataset()
    try:
        data=_source(db,p(db,1),"SOCIAL","11",90)
        types={x["type"] for x in data["tags"]}
        assert {"CANDIDATE","PROVINCE","SUSPECTED_VIOLATION","BAWASLU_ISSUE","ELECTORAL_ISSUE"}<=types
        assert "Riau" in data["suggested_provinces"]
        assert any(tag["type"]=="PROVINCE" and tag["label"]=="Riau" for tag in data["tags"])
        assert data["verified_province"]==""
        assert all(not tag["verified"] for tag in data["tags"])
        with pytest.raises(HTTPException) as ex:
            create_case(NewCase(source_type="SOCIAL",source_id="11",campaign_id=90,
                department="Pengawasan",target_scope="PROVINCE",target_province="Riau"),
                db.get(User,1),db)
        assert ex.value.status_code==422
        assert db.query(CaseAssignment).count()==0
    finally:
        db.close()

def test_province_mentions_are_suggested_but_not_treated_as_incident_location():
    db=dataset()
    try:
        source=db.get(SocialListeningResult,11)
        source.text_content="BAWASLU Riau menyampaikan informasi umum tentang pengawasan pemilu."
        db.commit()
        data=_source(db,p(db,1),"SOCIAL","11",90)
        assert any(x["type"]=="PROVINCE" and x["label"]=="Riau" and
                   x["basis"]=="PROVINCE_MENTION_ONLY" and not x["verified"]
                   for x in data["tags"])
        assert data["verified_province"]==""
        with pytest.raises(HTTPException):
            _validate_route(data,p(db,1),"PROVINCE","Riau")
    finally:
        db.close()

def test_confirmed_jurisdiction_allows_national_to_riau_but_not_to_other_provinces():
    db=dataset()
    try:
        confirmed(db)
        admin=p(db,1)
        src=_source(db,admin,"SOCIAL","11",90)
        assert src["verified_province"]=="Riau"
        assert _validate_route(src,admin,"PROVINCE","Riau")=="Riau"
        with pytest.raises(HTTPException):
            _validate_route(src,admin,"PROVINCE","Bali")
        with pytest.raises(HTTPException):
            _validate_route(src,p(db,3),"PROVINCE","Riau")
        case=create_case(NewCase(source_type="SOCIAL",source_id="11",campaign_id=90,
            department="Pengawasan",target_scope="PROVINCE",target_province="Riau",
            assignee_id=2,notes="Review the incident jurisdiction"),db.get(User,1),db)
        assert case["target_province"]=="Riau"
        row=db.get(CaseAssignment,case["id"])
        assert _visible(row,p(db,2),2)
        assert not _visible(row,p(db,3),3)
        assert _visible(row,p(db,1),1)
    finally:
        db.close()

def test_report_author_cannot_self_approve_and_another_validator_can():
    db=dataset()
    try:
        confirmed(db)
        case=create_case(NewCase(source_type="SOCIAL",source_id="11",campaign_id=90,
            department="Penanganan Pelanggaran",target_scope="NATIONAL"),
            db.get(User,1),db)
        result=create_report(case["id"],ReportDraft(title="Riau oversight report",
            executive_summary="One source refers to an alleged incident.",
            findings="The source alleges misconduct, without independent corroboration.",
            verification_notes="Original documents and source provenance require checking.",
            recommendations="Refer to authorized officers for verification."),db.get(User,1),db)
        report=db.get(CaseReport,result["id"])
        report.status="SUBMITTED"
        db.commit()
        with pytest.raises(HTTPException) as ex:
            transition_report(report.id,ReportAction(status="APPROVED"),db.get(User,1),db)
        assert ex.value.status_code==403
        approved=transition_report(report.id,ReportAction(status="APPROVED"),
                                   db.get(User,4),db)
        assert approved["status"]=="APPROVED"
    finally:
        db.close()

def test_a_regency_role_never_reads_an_unrelated_provincial_case():
    db=dataset()
    try:
        case=CaseAssignment(id=99,title="Riau case",source_type="SOCIAL",source_id="11",
            originating_scope="PROVINCE",originating_province="Riau",
            target_scope="PROVINCE",target_province="Riau",verified_province="Riau",
            target_department="Pengawasan",created_by=2)
        regency={"status":"Active","permissions":default_permissions("Regency/City Officer"),
            "geographic_scope":"Regency/City","province":"Riau"}
        assert not _visible(case,regency,123)
        assert _visible(case,regency,2)
    finally:
        db.close()


def test_assistant_handoff_requires_confirmation_and_no_duplicate_case():
    db=dataset()
    try:
        request=AssistantHandoff(source_type="SOCIAL",source_id="11",campaign_id=90,
            department="Penanganan Pelanggaran",target_scope="NATIONAL",
            title="Review atas dokumen pencalonan",executive_summary="Ada dugaan dalam unggahan.",
            findings="Sumber mengangkat klaim terkait pencalonan; perlu dokumen primer.",
            review_steps=["Periksa dokumen resmi sebelum menyimpulkan."],
            question="Analisis isu pencalonan Gibran",confirm=False)
        with pytest.raises(HTTPException) as denied:
            assistant_handoff(request,db.get(User,1),db)
        assert denied.value.status_code==422
        assert db.query(CaseAssignment).count()==0
        request.confirm=True
        saved=assistant_handoff(request,db.get(User,1),db)
        assert saved["existing"] is False
        assert saved["paid_provider_called"] is False
        assert saved["review_required"] is True
        case=db.get(CaseAssignment,saved["case"]["id"])
        report=db.get(CaseReport,saved["report_id"])
        assert case.target_department=="Penanganan Pelanggaran"
        assert case.status=="OPEN"
        assert report.status=="DRAFT" and "dokumen primer" in report.findings
        assert "belum dinyatakan terverifikasi" in report.verification_notes
        assert "Periksa dokumen resmi" in report.recommendations
        assert db.query(CaseTransition).filter_by(case_id=case.id,action="ASSISTANT_HANDOFF").count()==1
        again=assistant_handoff(request,db.get(User,1),db)
        assert again["existing"] is True
        assert again["case"]["id"]==case.id
        assert db.query(CaseReport).count()==1
    finally:
        db.close()


def test_assistant_handoff_rechecks_verified_province_and_acl():
    db=dataset()
    try:
        incoming=AssistantHandoff(source_type="SOCIAL",source_id="11",campaign_id=90,
            department="Pengawasan",target_scope="PROVINCE",
            target_province="Riau",assignee_id=2,confirm=True)
        with pytest.raises(HTTPException) as err:
            assistant_handoff(incoming,db.get(User,1),db)
        assert err.value.status_code==422
        confirmed(db)
        created=assistant_handoff(incoming,db.get(User,1),db)
        case=db.get(CaseAssignment,created["case"]["id"])
        assert case.target_province=="Riau" and case.assignee_id==2
        assert _visible(case,p(db,2),2)
        assert not _visible(case,p(db,3),3)
        assert assistant_workspace(db.get(User,2),db)["my_assignments"]==1
        assert assistant_workspace(db.get(User,3),db)["visible_open_cases"]==0
    finally:
        db.close()


def test_viewer_cannot_execute_assistant_handoff():
    db=dataset()
    try:
        db.add(User(id=8,email="viewer@test.invalid",full_name="Viewer",password_hash="unused"))
        db.add(AccessGrant(user_id=8,access_role="Viewer",geographic_scope="Nationwide",
            status="Active",permissions_json=json.dumps(default_permissions("Viewer"))))
        db.commit()
        with pytest.raises(HTTPException) as err:
            assistant_handoff(AssistantHandoff(source_type="SOCIAL",source_id="11",
                campaign_id=90,department="Pengawasan",confirm=True),db.get(User,8),db)
        assert err.value.status_code==403
        assert db.query(CaseAssignment).count()==0
    finally:
        db.close()


def test_fresh_relevant_posts_rank_above_old_hashtag_sources_without_invented_counts():
    from app.assistant_orchestration import _social_select
    from datetime import date,timedelta
    now=date.today().isoformat()
    old=(date.today()-timedelta(days=1000)).isoformat()
    posts=[
        {"id":"10","text_content":"Gibran laporan berita terkait pemilu dan pengawasan",
         "relevance_label":"RELEVANT","published_at":old,"campaign_name":"Bawaslu","engagement_total":100000},
        {"id":"20","text_content":"Gibran membahas dokumen pencalonan dan pemeriksaan",
         "relevance_label":"RELEVANT","published_at":now,"campaign_name":"Bawaslu","engagement_total":100},
    ]
    selected,total=_social_select(posts,"analisis audiens tentang Gibran",limit=2)
    assert total==2
    assert selected[0]["id"]=="20"
    assert selected[1]["id"]=="10"
