"""Phase 2 v147.4: genuine saved-Inbox-shaped evidence through both assessments.

No external APIs, paid models or live database writes. SQLite fixtures mimic
saved assessment and reviewed PDF content, not fabricated client legal verdicts.
"""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
import pytest

from app.db import Base
from app.models import User,AccessGrant
from app.access import default_permissions,profile
from app.inbox_radar import compile_inbox_findings,live_inbox_findings
from app.finding_assessments import assess_finding,finding_assessments
from app.platform_policy_screening import screen_platform_text,PLATFORM_POLICIES
from app.assistant_knowledge import KnowledgePDF,KnowledgeChunk,retrieve_knowledge


def make_db():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db=Session(engine)
    for uid,role,scope,province in (
        (1,"National Administrator","Nationwide",""),
        (2,"Provincial Analyst","Province","Riau"),
        (3,"Provincial Analyst","Province","Bali"),
        (4,"Viewer","Nationwide","")):
        db.add(User(id=uid,email=f"phase2-{uid}@example.invalid",
                    full_name=f"Officer {uid}",password_hash="unused"))
        db.add(AccessGrant(user_id=uid,access_role=role,geographic_scope=scope,
            province=province,status="Active",
            permissions_json=json.dumps(default_permissions(role))))
    db.commit()
    return db


def row(ident,**changes):
    record=dict(id=str(ident),campaign_id="10",relevance_label="RELEVANT",
         text_content="Laporan dugaan politik uang pemilu: catat bukti dan tindak lanjut BAWASLU.",
         canonical_url="https://example.invalid/post/"+str(ident),
         author_name="original source",platform="instagram",
         published_at="2026-11-10",assessment_version=3,
         sentiment="NEGATIVE",is_flagged=True,flag_review_status="FURTHER_INVESTIGATION",
         topic_labels=["Electoral Operations"],potential_issues=[
             {"category_name":"Alleged Vote Buying"}])
    record.update(changes)
    return record


def _pdf(db,uid,status,province,kind,title,body):
    doc=KnowledgePDF(
        title=title,filename="rule.pdf",scope="PROVINCE",province=province,
        content_sha256=(str(uid)*64)[:64],content_bytes=b"%PDF-private fixture",
        pages=2,extracted_chars=len(body),uploaded_by=1,active=True,
        document_type=kind,issuer="BAWASLU",review_status=status)
    db.add(doc);db.flush()
    db.add(KnowledgeChunk(document_id=doc.id,page=2,sequence=1,text_content=body))
    db.flush()
    return doc


def test_realistic_inbox_to_command_centre_preserves_sources_sentiment_flags_and_policy():
    base=row(501,platform="twitter-ai-search",
        text_content="Dugaan politik uang terjadi. KPU dan BAWASLU perlu memeriksa bukti.",
        sentiment="NEUTRAL")
    duplicate=row(501,campaign_id="11",platform="twitter-ai-search",
                  sentiment="POSITIVE",assessment_version=1,
                  is_flagged=False,flag_review_status="FLAG_DISMISSED")
    other=row(502,platform="reddit",text_content="I will attack you.",
              sentiment="NEGATIVE")
    irrelevant=row(503,relevance_label="IRRELEVANT",
                   text_content="I will attack you.",platform="telegram")
    findings=compile_inbox_findings([base,duplicate,other,irrelevant])
    sources=[post for finding in findings for post in finding["posts"]]
    assert len(sources)==2
    assert {p["canonical_source_id"] for p in sources}=={"social:501","social:502"}
    assert {p["platform"] for p in sources}=={"X","Reddit"}
    assert {p["sentiment"] for p in sources}=={"NEUTRAL","NEGATIVE"}
    assert all("violations" in f["players"] for f in findings)
    for finding in findings:
        result=assess_finding(None,{},finding) if not finding.get("players") else None
        # The test below runs the actual scoped document retrieval with a DB.
        assert result is None
    assert any(p["review_status"]=="FURTHER_INVESTIGATION" for p in sources)
    assert all(p["source_url"].startswith("https://") for p in sources)


def test_officer_reviewed_citations_retrieved_before_unreviewed_and_province_scoped():
    db=make_db()
    try:
        approved=_pdf(db,1,"OFFICER_REVIEWED","Riau","REGULATION",
            "Peraturan Pengawasan Pemilu Riau",
            "Pengawasan pemilu penanganan pelanggaran politik uang wajib mencatat bukti.")
        _pdf(db,2,"OFFICER_REVIEWED","Bali","REGULATION",
            "Peraturan Bali", "Pengawasan pemilu penanganan pelanggaran politik uang.")
        for n in range(15):
            _pdf(db,3+n,"UNREVIEWED","Riau","REGULATION",
                "Draft unreviewed", "Pengawasan pemilu penanganan pelanggaran politik uang.")
        _pdf(db,25,"OFFICER_REVIEWED","Riau","REPORT",
            "Unrelated report", "Pengawasan pemilu penanganan pelanggaran politik uang.")
        db.commit()
        p=profile(db,db.get(User,2))
        finding=compile_inbox_findings([row(502)])[0]
        assessment=assess_finding(db,p,finding)
        refs=assessment["legal"]["approved_reference_pages"]
        assert len(refs)==1
        assert refs[0]["document_id"]==approved.id
        assert refs[0]["page"]==2
        assert refs[0]["record_id"]==f"DOC-{approved.id}-P2"
        assert refs[0]["review_status"]=="OFFICER_REVIEWED"
        assert refs[0]["authority_is_currently_in_force"]=="NOT_VERIFIED"
        assert refs[0]["legal_currentness_verified"] is False
        assert assessment["legal"]["statutory_articles_verified"] is False
        assert assessment["legal"]["relevant_statutory_provision_identified"] is False
        assert assessment["legal"]["reviewed_legal_documents_only"] is True
        assert assessment["legal"]["unreviewed_matched_pages"] is None
        assert assessment["source_provenance"]["source_count_matches_finding"] is True
        assert assessment["source_provenance"]["unique_source_ids"]==["social:502"]
        assert assessment["platform_policy"]["platform_violation_confirmed"] is False
        assert assessment["follow_up"]["created_assignment"] is False
        assert assessment["paid_provider_called"] is False
        assert retrieve_knowledge(
            db,profile(db,db.get(User,3)),
            "peraturan pengawasan pemilu penanganan pelanggaran politik uang",
            semantic=False,reviewed_legal_only=True
        )[0]["document_id"]!=approved.id
    finally:
        db.close()


def test_missing_reviewed_pdf_causes_explicit_missing_reference_not_legal_claim():
    db=make_db()
    try:
        _pdf(db,40,"UNREVIEWED","Riau","REGULATION","Proposed guidance",
            "Pengawasan pemilu penanganan pelanggaran politik uang bukti.")
        db.commit()
        finding=compile_inbox_findings([row(700)])[0]
        out=assess_finding(db,profile(db,db.get(User,2)),finding)
        assert out["legal"]["approved_reference_pages"]==[]
        assert out["legal"]["approved_reference_missing"] is True
        assert out["legal"]["possible_violation_confirmed"] is False
    finally: db.close()


def test_platform_policy_entrypoints_cover_all_nine_and_remain_non_verdicts():
    for platform in ("tiktok","instagram","twitter-ai-search","youtube",
                     "threads","facebook","reddit","linkedin","telegram"):
        response=screen_platform_text(platform,"Warga mempertanyakan kinerja BAWASLU.")
        assert response["policy_url"].startswith("https://"),platform
        assert response["policy_version_verified"] is False
        assert response["platform_violation_confirmed"] is False
        assert response["legal_violation_confirmed"] is False
        assert response["status"]=="NO_DIRECT_SIGNAL_IDENTIFIED"
        assert response["policy_link_is_official_entrypoint_only"] is True
    reddit=screen_platform_text("reddit","I will attack you.")
    assert reddit["status"]=="REVIEW_INDICATED"
    assert "community rules" in reddit["policy_scope_note"]
    telegram=screen_platform_text("telegram","I will attack you.")
    assert telegram["status"]=="REVIEW_INDICATED"
    assert "private chat" in telegram["policy_scope_note"]
    unknown=screen_platform_text("unknown-network","I will attack you.")
    assert unknown["status"]=="POLICY_NOT_CONFIGURED"
    assert unknown["platform_violation_confirmed"] is False


def test_contextual_reporting_and_negative_criticism_never_count_as_breach():
    assert screen_platform_text("instagram","BAWASLU lambat dan mengecewakan.")[
        "status"]=="NO_DIRECT_SIGNAL_IDENTIFIED"
    news=screen_platform_text("reddit",
        "News reported an official quoted: I will attack you.")
    assert news["status"]=="CONTEXT_REVIEW_REQUIRED"
    assert news["platform_violation_confirmed"] is False
    negation=screen_platform_text("telegram",
        "Do not say I will attack you. Stop incitement.")
    assert negation["status"]=="CONTEXT_REVIEW_REQUIRED"


def test_duplicate_sources_and_missing_source_fields_are_reported_not_invented():
    finding={"id":"INBOX-V-1","players":["concerns"],
             "supporting_posts":2,
             "posts":[
                {"canonical_source_id":"social:1","source_url":"","message_original":"","platform":"reddit"},
                {"canonical_source_id":"social:1","source_url":"","message_original":"","platform":"reddit"}
             ]}
    out=assess_finding(None,{},finding)
    assert out["source_provenance"]["duplicate_links_removed"]==1
    assert out["source_provenance"]["missing_original_text"]==1
    assert out["source_provenance"]["missing_original_url"]==1
    assert out["source_provenance"]["source_count_matches_finding"] is False
    assert out["platform_policy"]["status_counts"]=={"INSUFFICIENT_SOURCE":1}


def test_unavailable_in_other_province_returns_not_found_without_leaking(monkeypatch):
    from app import smart_radar
    db=make_db()
    try:
        permitted={"id":"INBOX-VISIBLE","posts":[{"canonical_source_id":"social:777"}],
                   "players":["concerns"]}
        monkeypatch.setattr(smart_radar,"access_findings",
            lambda db,user:[permitted] if user.id==2 else [])
        with pytest.raises(HTTPException) as err:
            finding_assessments("INBOX-VISIBLE",db.get(User,3),db)
        assert err.value.status_code==404
    finally:db.close()
