"""v186.8: full-field data governance, append-only provenance and missing-source QA."""
import os
import pytest
from fastapi import HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.db import engine
from app.models import (AccessGrant,AuditEvent,CampaignEvidence,EvidenceAssessment,
                        MonitoringCampaign,SocialListeningResult,SocialListeningRun,User)
from app.inbox_human_gate import review_source
from app.inbox_human_corrections import decide_information,DecisionIn
from app.inbox_human_full_review_v1868 import (
    FieldPatch, FullReviewBatch, SecondReviewIn, ManualEvidenceIn,
    FIELD_GROUPS,full_review,save_full_review,secondary_review,
    manual_intake_create,manual_intake_list, _safe_url,
)
from app.inbox_human_handoff import gate2_handoff_preview,source_feedback
from scripts.seed_gate1_render_qa_v1866 import ADMIN_EMAIL,VIEWER_EMAIL,bootstrap


def _local_only(monkeypatch):
    if os.getenv("BAWASLU_ALLOW_ISOLATED_DB_TEST")!="YES":
        pytest.skip("Opt-in disposable localhost PostgreSQL CI only")
    for k,v in {
        "BAWASLU_INBOX_GATE1_READ_ENABLED":"true",
        "BAWASLU_INBOX_GATE1_WRITE_ENABLED":"true",
        "BAWASLU_INBOX_GATE1_PILOT_MODE":"staging",
        "BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS":"9",
        "BAWASLU_INBOX_GATE1_REAL_QA_CAMPAIGN_ID":"9",
        "BAWASLU_INBOX_GATE1_REAL_QA_CONFIRM":"POLITIK_UANG_AUDIT_ONLY",
    }.items():monkeypatch.setenv(k,v)


def test_full_field_workbench_and_manual_intake(monkeypatch):
    _local_only(monkeypatch)
    bootstrap()
    with Session(engine) as db:
        admin=db.scalar(select(User).where(User.email==ADMIN_EMAIL))
        viewer=db.scalar(select(User).where(User.email==VIEWER_EMAIL))
        admin_grant=db.scalar(select(AccessGrant).where(AccessGrant.user_id==admin.id))
        run=db.scalar(select(SocialListeningRun))
        reviewer=User(email="second-gate1-reviewer@example.invalid",
                      full_name="Independent CI reviewer",password_hash=hash_password("Second-CI-only-reviewer-1868!"))
        db.add(reviewer);db.flush()
        db.add(AccessGrant(user_id=reviewer.id,access_role="National Administrator",
                           geographic_scope="Nationwide",permissions_json=admin_grant.permissions_json,
                           status="Active"))
        for i in range(2,9):
            db.add(MonitoringCampaign(name=f"Other QA {i}",status="DRAFT",created_by=str(admin.id)))
        db.flush()
        campaign=MonitoringCampaign(name="Politik Uang",status="DRAFT",created_by=str(admin.id))
        db.add(campaign);db.flush()
        assert campaign.id==9
        source=SocialListeningResult(run_id=run.id,provider="QA_CI_ONLY",
                                     provider_result_id="FAKE-1868",
                                     platform="youtube",canonical_url="https://example.invalid/source",
                                     author_name="Unverified API author",
                                     text_content="Fictional provider text: politics",
                                     content_fingerprint="full-qa-ci-1868")
        db.add(source);db.flush()
        db.add(CampaignEvidence(campaign_id=9,result_id=source.id,match_method="KEYWORD"))
        ai=EvidenceAssessment(campaign_id=9,result_id=source.id,assessment_version=2,
                              model_version="FICTIONAL_CI",relevance_label="RELEVANT",
                              sentiment="NEUTRAL",explanation="Fictional assessment")
        db.add(ai);db.commit()
        sid=source.id;aid=ai.id
        before_source=db.scalar(select(func.count()).select_from(SocialListeningResult))
        before_ai=db.scalar(select(func.count()).select_from(EvidenceAssessment))
        detail=review_source(9,sid,admin,db)
        snapshot=full_review(9,sid,admin,db)
        assert len(FIELD_GROUPS)==3
        assert snapshot["can_edit"] is True and snapshot["revision"]==0
        assert snapshot["fields"]["author_name"]["original"]=="Unverified API author"
        assert snapshot["fields"]["author_name"]["effective"]=="Unverified API author"
        patches=[
            FieldPatch(field="author_name",value="Officer supplied author",
                       verification="SOURCE_CONFIRMED",evidence_url="https://example.invalid/author",
                       field_reason="Original author checked against public page"),
            FieldPatch(field="transcript",value="Fictional checked transcript missing in API",
                       mode="MISSING_PROVIDER",verification="OFFICER_SUPPLIED",
                       field_reason="The provider response was missing transcript"),
            FieldPatch(field="evidence_quality",value="PARTIAL",
                       field_reason="API response omits part of the content"),
        ]
        req=FullReviewBatch(fields=patches,expected_revision=0,expected_assessment_id=aid,
                             expected_source_digest=detail["source_integrity_digest"],
                             reason="Field-by-field correction for fictional QA data")
        result=save_full_review(9,sid,req,admin,db)
        assert result["saved"] and result["fields_saved"]==3
        assert result["secondary_review_required"]
        after=full_review(9,sid,admin,db)
        assert after["revision"]==result["revision"]
        assert after["fields"]["author_name"]["original"]=="Unverified API author"
        assert after["fields"]["author_name"]["effective"]=="Officer supplied author"
        assert after["fields"]["transcript"]["verification"]=="OFFICER_SUPPLIED"
        assert after["secondary_review"]["status"]=="PENDING"
        assert db.get(SocialListeningResult,sid).author_name=="Unverified API author"
        assert db.get(EvidenceAssessment,aid).relevance_label=="RELEVANT"
        assert db.scalar(select(func.count()).select_from(SocialListeningResult))==before_source
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment))==before_ai
        with pytest.raises(HTTPException) as stale:
            save_full_review(9,sid,req,admin,db)
        assert stale.value.status_code==409
        with pytest.raises(HTTPException) as self_review:
            secondary_review(9,sid,SecondReviewIn(
                expected_revision=result["revision"],expected_assessment_id=aid,
                expected_source_digest=detail["source_integrity_digest"],
                status="APPROVED",reason="Second reviewer cannot be the first"),admin,db)
        assert self_review.value.status_code==403
        decision=DecisionIn(status="OFFICER_VERIFIED",expected_revision=0,
                            expected_assessment_id=aid,expected_sentiment_revision=0,
                            expected_source_digest=detail["source_integrity_digest"],
                            expected_enrichment_revision=result["revision"],
                            reason="Information reviewed with supporting data")
        with pytest.raises(HTTPException) as needs_second:
            decide_information(9,sid,decision,admin,db)
        assert needs_second.value.status_code==422
        with pytest.raises(HTTPException) as viewer_error:
            save_full_review(9,sid,FullReviewBatch(
                fields=[FieldPatch(field="language",value="id",
                    field_reason="Viewer not authorized to correct sources")],
                expected_revision=result["revision"],expected_assessment_id=aid,
                expected_source_digest=detail["source_integrity_digest"],
                reason="Viewer should never write corrections"),viewer,db)
        assert viewer_error.value.status_code==403
        reviewed=secondary_review(9,sid,SecondReviewIn(
            expected_revision=result["revision"],expected_assessment_id=aid,
            expected_source_digest=detail["source_integrity_digest"],
            status="APPROVED",reason="Independently checked fictional author metadata"),reviewer,db)
        assert reviewed["saved"] and reviewed["status"]=="APPROVED"
        assert full_review(9,sid,admin,db)["secondary_review"]["status"]=="APPROVED"
        assert decide_information(9,sid,decision,admin,db)["saved"]
        assert review_source(9,sid,admin,db)["information_review_status"]=="OFFICER_VERIFIED"
        feedback=source_feedback(9,sid,admin,db)
        assert any(f["field"]=="enrichment" and f["correction_current"] for f in feedback["items"])
        packet=gate2_handoff_preview(9,sid,admin,db)
        assert packet["readiness"]=="BLOCKED"
        assert "QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION" in packet["review_blockers"]
        assert packet["command_centre_published"] is False
        manual=manual_intake_create(9,ManualEvidenceIn(
            platform="youtube",title="API missed a fictional post",
            text_content="Fictional manually sourced missing post for QA only.",
            source_url="https://example.invalid/manual-evidence",
            reason="Provider API did not return this fictional post"),admin,db)
        assert manual["saved"] and manual["status"]=="QA_UNVERIFIED"
        assert manual["created_in_social_listening"] is False
        records=manual_intake_list(9,admin,db)
        assert records["items"][0]["title"]=="API missed a fictional post"
        assert records["items"][0]["status"]=="QA_UNVERIFIED"
        assert db.scalar(select(func.count()).select_from(SocialListeningResult))==before_source
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment))==before_ai
        with pytest.raises(HTTPException) as badurl:
            _safe_url("javascript:alert(1)",True)
        assert badurl.value.status_code==422
        db.add(CampaignEvidence(campaign_id=8,result_id=sid,match_method="KEYWORD"))
        db.commit()
        assert full_review(9,sid,admin,db)["can_edit"] is False
        with pytest.raises(HTTPException) as shared:
            save_full_review(9,sid,FullReviewBatch(
                fields=[FieldPatch(field="language",value="id",
                     field_reason="Shared source must not be corrected")],
                expected_revision=result["revision"],expected_assessment_id=aid,
                expected_source_digest=detail["source_integrity_digest"],
                reason="Disallow writes to cross-linked operational record"),admin,db)
        assert shared.value.status_code==403
        assert db.scalar(select(func.count()).select_from(SocialListeningResult))==before_source
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment))==before_ai
        assert db.scalar(select(func.count()).select_from(AuditEvent).where(
            AuditEvent.action=="GATE1_QA_FULL_RECORD_ENRICHED"))==1


def test_ui_and_server_safety_contract():
    from pathlib import Path
    root=Path(__file__).parents[2]
    ui=(root/"frontend/src/components/intel/Gate1FullWorkbench.jsx").read_text()
    api=(root/"frontend/src/api/base44Client.js").read_text()
    assert 'gate1-full-field-workbench' in ui
    assert 'gate1-manual-intake' in ui
    assert 'gate1-secondary-review' in ui
    assert 'saveFullReview:' in api
    assert 'manualIntake:' in api
    backend=(root/"backend/app/inbox_human_full_review_v1868.py").read_text()
    assert "official_intelligence_published" in backend
    assert "original_source_preserved" in backend
