"""v186.1: isolated PostgreSQL Gate 1 pilot (never use operational database).

Tests real PostgreSQL row locks, corrections, audit history, source snapshot
staleness, rollback and pilot authorization. Synthetic fictional sources only.
This test skips unless an explicitly authorized, local disposable CI database
is configured. It cannot run against Supabase or Render hosts.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.db import Base
from app.models import (
    AccessGrant, AuditEvent, CampaignEvidence, EvidenceAssessment,
    MonitoringCampaign, SocialListeningResult, SocialListeningRun, User,
)
from app.officer_sentiment import OfficerSentimentCorrection
from app import inbox_human_corrections as gate
from app import inbox_human_gate as review_api
from app.inbox_gate_integrity import source_integrity_digest


def _isolated_database_url():
    if os.getenv("BAWASLU_ALLOW_ISOLATED_DB_TEST") != "YES":
        pytest.skip("Isolated PostgreSQL pilot is opt-in only")
    url = os.getenv("BAWASLU_TEST_DATABASE_URL", "")
    parsed = urlsplit(url.replace("postgresql+psycopg://", "postgresql://", 1))
    if not (parsed.scheme == "postgresql"
            and parsed.hostname in {"localhost", "127.0.0.1"}
            and parsed.port == 5432
            and parsed.path == "/bawaslu_gate1_pilot_ci"):
        pytest.fail("Refusing non-local or non-disposable PostgreSQL database")
    return url


@pytest.fixture
def isolated_pilot(monkeypatch):
    url = _isolated_database_url()
    # No external provider calls, no remote database, no purchased AI credits.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("SOCIALCRAWL_API_KEY", "")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED", "true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED", "false")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE", "staging")
    engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        pytest.fail("A real PostgreSQL backend is required")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(gate, "_refresh_views", lambda: None)
    SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionFactory() as db:
        user = User(
            email="gate1-officer@example.invalid", full_name="QA Pilot Officer",
            password_hash="DISABLED_TEST_LOGIN",
        )
        db.add(user)
        db.flush()
        db.add(AccessGrant(
            user_id=user.id, access_role="National Administrator",
            geographic_scope="Nationwide", status="Active",
            permissions_json=json.dumps({
                "view_intelligence": True, "human_validation": True,
                "edit_intelligence": True, "administration": True,
                "add_intelligence": True,
            }),
        ))
        campaign = MonitoringCampaign(
            name=gate.PILOT_QA_CAMPAIGN_NAME, status="DRAFT",
            created_by=str(user.id), primary_keywords_json="[]",
            platforms_json="[]", next_run_at=None,
        )
        other = MonitoringCampaign(
            name="Normal operational campaign", status="ACTIVE",
            created_by=str(user.id), primary_keywords_json="[]",
            platforms_json="[]", next_run_at=None,
        )
        db.add_all([campaign, other])
        db.flush()
        run = SocialListeningRun(
            provider=gate.PILOT_QA_PROVIDER, query_json='{"pilot":true}',
            status="COMPLETED", credits_used=0, result_count=1,
            executed_by="isolated-ci-only",
        )
        db.add(run)
        db.flush()
        post = SocialListeningResult(
            run_id=run.id, provider=gate.PILOT_QA_PROVIDER,
            provider_result_id="GATE1-QA-FICTIONAL-POST-001",
            platform="facebook", content_type="post",
            author_name="Synthetic fictional test author",
            text_content="Synthetic QA discussion: a fictional community election forum.",
            canonical_url="https://example.invalid/qa/fictional-1",
            raw_payload_json='{"qa_only":true,"never_collected":true}',
            source_identity_json='{"qa_only":true}',
            geography_json='{}', review_state="QA_ONLY",
        )
        real_post = SocialListeningResult(
            run_id=run.id, provider="SOCIALCRAWL",
            provider_result_id="ORDINARY-REFUSED-POST",
            text_content="Synthetic non-allowlisted source for denial test",
            raw_payload_json='{"qa_only":true}', geography_json='{}',
        )
        db.add_all([post, real_post])
        db.flush()
        db.add_all([
            CampaignEvidence(campaign_id=campaign.id, result_id=post.id,
                             match_method="QA_SYNTHETIC"),
            CampaignEvidence(campaign_id=campaign.id, result_id=real_post.id,
                             match_method="KEYWORD"),
            CampaignEvidence(campaign_id=other.id, result_id=post.id,
                             match_method="QA_SYNTHETIC"),
        ])
        baseline = EvidenceAssessment(
            campaign_id=campaign.id, result_id=post.id, assessment_version=1,
            model_version="QA_OFFLINE_BASELINE", relevance_label="IRRELEVANT",
            sentiment="NEGATIVE", explanation="Synthetic QA baseline",
        )
        real_assessment = EvidenceAssessment(
            campaign_id=campaign.id, result_id=real_post.id, assessment_version=1,
            model_version="QA_OFFLINE_BASELINE", relevance_label="RELEVANT",
            sentiment="NEUTRAL", explanation="Synthetic disallowed provider",
        )
        other_assessment = EvidenceAssessment(
            campaign_id=other.id, result_id=post.id, assessment_version=1,
            model_version="QA_OFFLINE_BASELINE", relevance_label="UNCERTAIN",
            sentiment="NEUTRAL",
        )
        db.add_all([baseline, real_assessment, other_assessment])
        db.commit()
        data = {
            "user_id": user.id, "campaign_id": campaign.id,
            "other_campaign_id": other.id, "source_id": post.id,
            "blocked_source_id": real_post.id,
            "baseline_id": baseline.id, "raw_payload": post.raw_payload_json,
        }
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS", str(data["campaign_id"]))
    try:
        yield SessionFactory, data
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def _source(db, data):
    return db.get(SocialListeningResult, data["source_id"])


def _body(db, data, field="relevance", value="RELEVANT"):
    assessment = gate._latest_assessment(db, data["campaign_id"], data["source_id"])
    sentiment = gate._latest_sentiment(db, data["campaign_id"], data["source_id"])
    return gate.FieldCorrectionIn(
        field=field, value=value,
        expected_revision=assessment.assessment_version if field=="relevance"
                          else (sentiment.id if sentiment else 0),
        expected_assessment_id=assessment.id,
        expected_source_digest=source_integrity_digest(_source(db,data)),
        reason="Review of fictional QA-only election discussion",
    )


def _call_correct(db, data, body):
    return gate.correct_field(
        data["campaign_id"], data["source_id"], body,
        user=db.get(User, data["user_id"]), db=db,
    )


def test_real_postgres_pilot_isolated_write_and_audit_workflow(isolated_pilot, monkeypatch):
    SessionFactory, data = isolated_pilot
    with SessionFactory() as db:
        user = db.get(User,data["user_id"])
        before = db.query(AuditEvent).count()
        initial = _body(db, data)
        assert review_api.gate1_pilot_readiness(data["campaign_id"],user=user,db=db)[
            "ready_for_write_pilot"] is False
        with pytest.raises(HTTPException) as denied:
            _call_correct(db,data,initial)
        assert denied.value.status_code==403
        assert db.query(AuditEvent).count()==before
        monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
        preflight = review_api.gate1_pilot_readiness(data["campaign_id"],user=user,db=db)
        assert preflight["pilot_campaign_draft_and_named"]
        assert preflight["non_synthetic_link_count"]==1
        assert preflight["ready_for_write_pilot"] is False
        # Disallowed source cannot be mutated even in an allowlisted campaign.
        assessment = gate._latest_assessment(db,data["campaign_id"],data["blocked_source_id"])
        blocked = db.get(SocialListeningResult,data["blocked_source_id"])
        with pytest.raises(HTTPException) as denied:
            gate.correct_field(
                data["campaign_id"], blocked.id,
                gate.FieldCorrectionIn(
                    field="relevance",value="IRRELEVANT",
                    expected_revision=1,expected_assessment_id=assessment.id,
                    expected_source_digest=source_integrity_digest(blocked),
                    reason="Synthetic real-provider denial regression",
                ), user=user,db=db,
            )
        assert denied.value.status_code==403
        # A different ordinary campaign stays protected even with QA source.
        with pytest.raises(HTTPException) as denied:
            gate.correct_field(
                data["other_campaign_id"],data["source_id"],
                gate.FieldCorrectionIn(
                    field="relevance",value="RELEVANT",
                    expected_revision=1,
                    expected_assessment_id=gate._latest_assessment(
                        db,data["other_campaign_id"],data["source_id"]).id,
                    expected_source_digest=source_integrity_digest(_source(db,data)),
                    reason="Different campaign must never inherit pilot access",
                ), user=user,db=db,
            )
        assert denied.value.status_code==403
        # Core append-only real PostgreSQL test.
        change = _call_correct(db,data,initial)
        assert change["saved"] and change["automatic_publication"] is False
        assert change["paid_provider_called"] is False
        assert gate._latest_assessment(db,data["campaign_id"],data["source_id"]).relevance_label=="RELEVANT"
        assert db.get(EvidenceAssessment,data["baseline_id"]).relevance_label=="IRRELEVANT"
        assert _source(db,data).raw_payload_json == data["raw_payload"]
        with pytest.raises(HTTPException) as stale:
            _call_correct(db,data,initial)
        assert stale.value.status_code==409
        sentiment = _call_correct(db,data,_body(db,data,"sentiment","NEUTRAL"))
        assert sentiment["saved"] and sentiment["effective_value"]=="NEUTRAL"
        assert gate._latest_sentiment(db,data["campaign_id"],data["source_id"]).sentiment=="NEUTRAL"
        latest = gate._latest_assessment(db,data["campaign_id"],data["source_id"])
        officer_sentiment = gate._latest_sentiment(db,data["campaign_id"],data["source_id"])
        review = gate.DecisionIn(
            status="OFFICER_VERIFIED",expected_revision=0,
            expected_assessment_id=latest.id,
            expected_sentiment_revision=officer_sentiment.id,
            expected_source_digest=source_integrity_digest(_source(db,data)),
            reason="Officer reviewed this fictional QA-only information snapshot",
        )
        decision = gate.decide_information(
            data["campaign_id"],data["source_id"],review,user=user,db=db,
        )
        assert decision["saved"] and decision["legal_claim_verified"] is False
        assert gate.review_state_for_source(db,data["campaign_id"],data["source_id"])[
            "information_review_status"]=="OFFICER_VERIFIED"
        _call_correct(db,data,_body(db,data,"sentiment","POSITIVE"))
        assert gate.review_state_for_source(db,data["campaign_id"],data["source_id"])[
            "information_review_status"]=="REVALIDATION_REQUIRED"
        current = gate._latest_assessment(db,data["campaign_id"],data["source_id"])
        restored = gate.restore_field(
            data["campaign_id"],data["source_id"],
            gate.RestoreIn(
                field="relevance",target_revision=1,
                expected_revision=current.assessment_version,
                expected_assessment_id=current.id,
                expected_source_digest=source_integrity_digest(_source(db,data)),
                reason="Restore original fictional QA relevance as new revision",
            ),user=user,db=db,
        )
        assert restored["revision"]==3
        assert gate._latest_assessment(db,data["campaign_id"],data["source_id"]).relevance_label=="IRRELEVANT"
        history = gate.correction_history(
            data["campaign_id"],data["source_id"],user=user,db=db,
        )
        assert [row["revision"] for row in history["relevance_history"][:3]]==[3,2,1]
        assert history["audit_history"][0]["action"]=="GATE1_FIELD_RESTORED"
        assert _source(db,data).raw_payload_json==data["raw_payload"]
        assert db.query(AuditEvent).filter(AuditEvent.subject_type=="Gate1InformationReview").count()>=5


def test_postgres_concurrent_update_has_single_winner(isolated_pilot, monkeypatch):
    SessionFactory, data = isolated_pilot
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
    with SessionFactory() as db:
        expected = _body(db,data)
    def worker(label):
        with SessionFactory() as db:
            try:
                return ("saved", _call_correct(
                    db, data, expected.model_copy(update={"value":label}),
                ))
            except HTTPException as exc:
                db.rollback()
                return ("rejected", exc.status_code)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker,["RELEVANT","UNCERTAIN"]))
    assert sorted(status for status,_ in results)==["rejected","saved"]
    assert [detail for status,detail in results if status=="rejected"]==[409]
    with SessionFactory() as db:
        rows = db.query(EvidenceAssessment).filter_by(
            campaign_id=data["campaign_id"],result_id=data["source_id"],
        ).order_by(EvidenceAssessment.assessment_version.asc()).all()
        assert [r.assessment_version for r in rows]==[1,2]
        assert db.query(AuditEvent).filter_by(
            subject_type="Gate1InformationReview",action="GATE1_FIELD_CORRECTED",
        ).count()==1


def test_qa_campaign_name_and_source_guard_fail_closed(isolated_pilot, monkeypatch):
    SessionFactory,data=isolated_pilot
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
    with SessionFactory() as db:
        user=db.get(User,data["user_id"])
        campaign=db.get(MonitoringCampaign,data["campaign_id"])
        original=campaign.name
        campaign.name="Operational campaign"
        db.commit()
        assert review_api.gate1_pilot_readiness(
            data["campaign_id"],user=user,db=db,
        )["ready_for_write_pilot"] is False
        with pytest.raises(HTTPException) as denied:
            _call_correct(db,data,_body(db,data))
        assert denied.value.status_code==403
        campaign.name=original
        campaign.status="ACTIVE"
        db.commit()
        with pytest.raises(HTTPException) as denied:
            _call_correct(db,data,_body(db,data))
        assert denied.value.status_code==403
