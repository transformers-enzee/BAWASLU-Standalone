"""v185.8: controlled, append-only Human Gate 1 corrections and review decisions.

Uses the existing EvidenceAssessment, OfficerSentimentCorrection and AuditEvent
tables; no schema migration, provider payload rewrite, model training or insight
publication. A historical restore is another audited correction, never a delete.
"""
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import current_user
from .db import get_db
from .access import has
from .models import AuditEvent, EvidenceAssessment, EvidenceReview, SocialListeningResult, User
from .officer_sentiment import OfficerSentimentCorrection
from .governance_persistence import _grant, _campaign, _source
from .inbox_human_gate import _read_enabled, _write_enabled
from .inbox_gate_integrity import (
    GATE1_AUDIT_SUBJECT, source_integrity_digest, review_projection, audit_payload,
)
from .socialcrawl import _result_in_scope

router = APIRouter(prefix="/api/inbox/human-review", tags=["inbox-human-review"])
RELEVANCE = frozenset(("RELEVANT", "HIGHLY_RELEVANT", "IRRELEVANT", "UNCERTAIN"))
SENTIMENT = frozenset(("POSITIVE", "NEUTRAL", "NEGATIVE"))
STATES = frozenset(("OFFICER_VERIFIED", "NEEDS_REVIEW", "HELD", "EXCLUDED"))
AUDIT_SUBJECT = GATE1_AUDIT_SUBJECT
# v186.1 staging-only write pilot: a campaign allowlist is not sufficient
# protection when staging and operational services may share a database.
PILOT_QA_CAMPAIGN_NAME = "BAWASLU Gate 1 QA Pilot"
PILOT_QA_PROVIDER = "GATE1_QA_SYNTHETIC"
PILOT_QA_SOURCE_PREFIX = "GATE1-QA-"
RELEVANCE_COPY = (
    "relevance_confidence", "sentiment", "sentiment_confidence", "sentiment_explanation",
    "sentiment_model", "candidate_signals_json", "geographic_signals_json",
    "potential_issue_signals_json", "topic_labels_json", "public_concern_signals_json",
    "attention_assessment_json", "player_summaries_json",
)


class FieldCorrectionIn(BaseModel):
    field: str
    value: str
    expected_revision: int = Field(ge=0)
    expected_assessment_id: int = Field(gt=0)
    expected_source_digest: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=10, max_length=1500)


class RestoreIn(BaseModel):
    field: str
    target_revision: int = Field(ge=0)
    expected_revision: int = Field(ge=0)
    expected_assessment_id: int = Field(gt=0)
    expected_source_digest: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=10, max_length=1500)


class DecisionIn(BaseModel):
    status: str
    expected_revision: int = Field(ge=0)
    expected_assessment_id: int | None = None
    expected_sentiment_revision: int = Field(ge=0)
    expected_source_digest: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=10, max_length=1500)


def _allowlist():
    parts = [v.strip() for v in os.getenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS", "").split(",") if v.strip()]
    if not parts or len(parts) > 10 or any(not v.isdecimal() or int(v) <= 0 for v in parts):
        return set()
    result = {int(v) for v in parts}
    return result if len(result) == len(parts) else set()


def is_pilot_qa_campaign(campaign):
    return bool(
        getattr(campaign, "name", "") == PILOT_QA_CAMPAIGN_NAME
        and getattr(campaign, "status", None) == "DRAFT"
    )


def is_pilot_qa_source(source):
    return bool(
        getattr(source, "provider", None) == PILOT_QA_PROVIDER
        and str(getattr(source, "provider_result_id", "") or "").startswith(
            PILOT_QA_SOURCE_PREFIX
        )
    )


def can_edit_gate1(profile, campaign):
    from .campaigns import _editable
    return bool(_write_enabled()
                and os.getenv("BAWASLU_INBOX_GATE1_PILOT_MODE", "").lower() == "staging"
                and is_pilot_qa_campaign(campaign)
                and campaign.id in _allowlist()
                and has(profile, "human_validation")
                and has(profile, "edit_intelligence")
                and _editable(profile, campaign))


def _authorize(db, user, campaign_id, result_id, write=False):
    _read_enabled()
    officer = _grant(db, user, "view_intelligence")
    campaign = _campaign(db, officer, campaign_id)
    source = _source(db, officer, campaign_id, result_id)
    if write and not can_edit_gate1(officer, campaign):
        raise HTTPException(403, "Human Gate 1 pilot correction authorization required")
    if write and not is_pilot_qa_source(source):
        raise HTTPException(403, "Pilot writes are limited to explicitly synthetic QA evidence")
    return officer, campaign, source


def _latest_assessment(db, campaign_id, result_id):
    return (db.query(EvidenceAssessment)
            .filter_by(campaign_id=campaign_id, result_id=result_id)
            .order_by(EvidenceAssessment.assessment_version.desc(), EvidenceAssessment.id.desc()).first())


def _latest_sentiment(db, campaign_id, result_id):
    return (db.query(OfficerSentimentCorrection)
            .filter_by(campaign_id=campaign_id, result_id=result_id)
            .order_by(OfficerSentimentCorrection.id.desc()).first())


def _decision_query(db, campaign_id, result_id):
    return db.query(AuditEvent).filter_by(
        subject_type=AUDIT_SUBJECT,
        subject_id=f"{campaign_id}:{result_id}",
        action="GATE1_INFORMATION_DECISION",
    )


def _latest_decision(db, campaign_id, result_id):
    return _decision_query(db, campaign_id, result_id).order_by(AuditEvent.id.desc()).first()


def _payload(event):
    return audit_payload(event)


def review_state_for_source(db, campaign_id, result_id, assessment=None, sentiment=None, source=None):
    event = _latest_decision(db, campaign_id, result_id)
    if assessment is None:
        assessment = _latest_assessment(db, campaign_id, result_id)
    if sentiment is None:
        sentiment = _latest_sentiment(db, campaign_id, result_id)
    if source is None:
        source = db.get(SocialListeningResult, result_id)
    return review_projection(event, assessment, sentiment, source)


def _write_audit(db, officer, campaign_id, result_id, action, changes):
    event = AuditEvent(
        subject_type=AUDIT_SUBJECT,
        subject_id=f"{campaign_id}:{result_id}",
        action=action,
        actor_id=str(officer["id"]),
        actor_name=str(officer.get("name") or "")[:255],
        changes_json=json.dumps({
            "campaign_id": campaign_id, "result_id": result_id,
            "original_source_preserved": True, "official_insight_published": False,
            "model_training_triggered": False, **changes,
        }, ensure_ascii=False, sort_keys=True),
        occurred_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(event)
    db.flush()
    return event


def _refresh_views():
    from .inbox_read_cache import invalidate as invalidate_inbox
    from .smart_radar import invalidate_dashboard_cache
    invalidate_inbox()
    invalidate_dashboard_cache()


def _lock_current_source(db, officer, source):
    """Refresh under a source-row lock before accepting any Gate 1 mutation."""
    locked = (db.query(SocialListeningResult)
              .filter_by(id=source.id).with_for_update().populate_existing().first())
    if locked is None or not _result_in_scope(db, officer, locked):
        raise HTTPException(404, "Source unavailable")
    return locked


def _apply_field(db, user, officer, source, campaign_id, field, value, expected_revision,
                 reason, action="GATE1_FIELD_CORRECTED", restored_from=None,
                 expected_assessment_id=None, expected_source_digest=None):
    field = field.strip().lower()
    value = value.strip().upper()
    if field not in ("relevance", "sentiment"):
        raise HTTPException(422, "Supported Gate 1 fields: relevance or sentiment")
    allowed = RELEVANCE if field == "relevance" else SENTIMENT
    if value not in allowed:
        raise HTTPException(422, "Invalid field value")
    # Serialize cooperating Gate 1 writers using an existing row lock, with
    # a separate optimistic revision check to reject stale browser submissions.
    source = _lock_current_source(db, officer, source)
    if expected_source_digest is not None and source_integrity_digest(source) != expected_source_digest:
        raise HTTPException(409, "Saved source changed; refresh before correcting")
    assessment = _latest_assessment(db, campaign_id, source.id)
    if assessment is None:
        raise HTTPException(422, "Saved assessment required before field correction")
    if expected_assessment_id is not None and assessment.id != expected_assessment_id:
        raise HTTPException(409, "Assessment changed; refresh before correcting")
    sentiment = _latest_sentiment(db, campaign_id, source.id)
    if field == "relevance":
        old_value = str(assessment.relevance_label or "UNASSESSED").upper()
        previous = int(assessment.assessment_version)
    else:
        old_value = str((sentiment.sentiment if sentiment else assessment.sentiment) or "UNKNOWN").upper()
        previous = sentiment.id if sentiment else 0
    if previous != expected_revision:
        raise HTTPException(409, "Source changed; refresh assessment and try again")
    if old_value == value:
        raise HTTPException(422, "This value is already effective; no correction recorded")
    if field == "relevance":
        fields = {name: getattr(assessment, name) for name in RELEVANCE_COPY}
        new = EvidenceAssessment(
            campaign_id=campaign_id, result_id=source.id,
            assessment_version=previous + 1,
            model_version="HUMAN_OVERRIDE", relevance_label=value,
            explanation=f"Human Gate 1: {reason[:1100]}", **fields,
        )
        db.add(new)
        db.flush()
        db.add(EvidenceReview(
            assessment_id=new.id, reviewer_id=str(user.id), decision=value,
            rationale=reason[:1500],
        ))
        revision, correction_id = new.assessment_version, new.id
    else:
        new = OfficerSentimentCorrection(
            campaign_id=campaign_id, result_id=source.id,
            sentiment=value, rationale=reason, actor_id=user.id,
        )
        db.add(new)
        db.flush()
        revision, correction_id = new.id, new.id
    _write_audit(db, officer, campaign_id, source.id, action, {
        "field_name": field, "provider_value": None,
        "provider_value_status": "retained_in_original_payload",
        "ai_value": (assessment.relevance_label if field == "relevance" else assessment.sentiment),
        "old_effective_value": old_value, "new_effective_value": value,
        "previous_revision": previous, "revision": revision,
        "reviewer_id": str(user.id), "reason": reason,
        "source_integrity_digest": source_integrity_digest(source),
        "assessment_id_before_correction": assessment.id,
        "model_version": assessment.model_version, "review_status": "FIELD_CORRECTED",
        "correction_id": correction_id, "restored_from": restored_from,
    })
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Concurrent correction; refresh before retrying")
    _refresh_views()
    return {
        "saved": True, "field": field, "effective_value": value,
        "revision": revision, "correction_id": correction_id,
        "review_status": "FIELD_CORRECTED", "revalidation_required": True,
        "paid_provider_called": False, "automatic_publication": False,
    }


@router.post("/campaign/{campaign_id}/source/{result_id}/corrections")
def correct_field(campaign_id: int, result_id: int, body: FieldCorrectionIn,
                  user: User=Depends(current_user), db: Session=Depends(get_db)):
    officer, campaign, source = _authorize(db, user, campaign_id, result_id, True)
    return _apply_field(db, user, officer, source, campaign_id,
                        body.field, body.value, body.expected_revision, body.reason.strip(),
                        expected_assessment_id=body.expected_assessment_id,
                        expected_source_digest=body.expected_source_digest)


@router.post("/campaign/{campaign_id}/source/{result_id}/restore")
def restore_field(campaign_id: int, result_id: int, body: RestoreIn,
                  user: User=Depends(current_user), db: Session=Depends(get_db)):
    officer, campaign, source = _authorize(db, user, campaign_id, result_id, True)
    field = body.field.strip().lower()
    if field == "relevance":
        old = (db.query(EvidenceAssessment)
               .filter_by(campaign_id=campaign_id, result_id=result_id,
                          assessment_version=body.target_revision).first())
        value = old.relevance_label if old else None
    elif field == "sentiment":
        if body.target_revision == 0:
            old = _latest_assessment(db, campaign_id, result_id)
            value = old.sentiment if old else None
        else:
            old = (db.query(OfficerSentimentCorrection)
                   .filter_by(campaign_id=campaign_id, result_id=result_id,
                              id=body.target_revision).first())
            value = old.sentiment if old else None
    else:
        raise HTTPException(422, "Unsupported restore field")
    if not value:
        raise HTTPException(404, "Selected historical revision not found")
    return _apply_field(
        db, user, officer, source, campaign_id, field, value, body.expected_revision,
        body.reason.strip(), action="GATE1_FIELD_RESTORED", restored_from=body.target_revision,
        expected_assessment_id=body.expected_assessment_id,
        expected_source_digest=body.expected_source_digest,
    )


@router.post("/campaign/{campaign_id}/source/{result_id}/decision")
def decide_information(campaign_id: int, result_id: int, body: DecisionIn,
                       user: User=Depends(current_user), db: Session=Depends(get_db)):
    officer, campaign, source = _authorize(db, user, campaign_id, result_id, True)
    status = body.status.strip().upper()
    if status not in STATES:
        raise HTTPException(422, "Invalid information review decision")
    source = _lock_current_source(db, officer, source)
    latest = _latest_decision(db, campaign_id, result_id)
    current = latest.id if latest else 0
    if body.expected_revision != current:
        raise HTTPException(409, "Review decision changed; refresh")
    assessment = _latest_assessment(db, campaign_id, result_id)
    sentiment = _latest_sentiment(db, campaign_id, result_id)
    digest = source_integrity_digest(source)
    if (body.expected_source_digest != digest
            or body.expected_assessment_id != (assessment.id if assessment else None)
            or body.expected_sentiment_revision != (sentiment.id if sentiment else 0)):
        raise HTTPException(409, "Evidence changed since opening; refresh before review")
    if status == "OFFICER_VERIFIED" and (
        assessment is None
        or str(assessment.relevance_label or "").upper() in ("", "UNASSESSED")
        or assessment.model_version == "PRISM_PENDING_OPENAI"
        or not (source.text_content or source.canonical_url)
    ):
        raise HTTPException(422, "A completed assessment and saved source trace are required")
    event = _write_audit(db, officer, campaign_id, result_id, "GATE1_INFORMATION_DECISION", {
        "status": status, "reason": body.reason.strip(),
        "previous_status": _payload(latest).get("status") if latest else None,
        "reviewer_id": str(user.id),
        "assessment_id": assessment.id if assessment else None,
        "sentiment_correction_id": sentiment.id if sentiment else None,
        "source_integrity_digest": digest,
        "model_version": assessment.model_version if assessment else None,
        "information_only": True, "legal_claim_verified": False,
    })
    db.commit()
    return {"saved": True, "status": status, "revision": event.id,
            "legal_claim_verified": False, "automatic_publication": False,
            "paid_provider_called": False}


@router.get("/campaign/{campaign_id}/source/{result_id}/history")
def correction_history(campaign_id: int, result_id: int,
                       user: User=Depends(current_user), db: Session=Depends(get_db)):
    _authorize(db, user, campaign_id, result_id)
    assessments = (db.query(EvidenceAssessment)
                   .filter_by(campaign_id=campaign_id, result_id=result_id)
                   .order_by(EvidenceAssessment.assessment_version.desc(),
                             EvidenceAssessment.id.desc()).limit(40).all())
    sentiments = (db.query(OfficerSentimentCorrection)
                  .filter_by(campaign_id=campaign_id, result_id=result_id)
                  .order_by(OfficerSentimentCorrection.id.desc()).limit(40).all())
    events = (db.query(AuditEvent)
              .filter_by(subject_type=AUDIT_SUBJECT, subject_id=f"{campaign_id}:{result_id}")
              .order_by(AuditEvent.id.desc()).limit(80).all())
    return {
        "relevance_history": [{
            "revision": row.assessment_version, "value": row.relevance_label,
            "model_version": row.model_version, "created_at": row.created_at.isoformat() if row.created_at else None,
        } for row in assessments],
        "sentiment_history": [{
            "revision": row.id, "value": row.sentiment, "reviewer_id": str(row.actor_id),
            "reason": row.rationale, "created_at": row.created_at.isoformat() if row.created_at else None,
        } for row in sentiments],
        "audit_history": [{
            "revision": row.id, "action": row.action, "reviewer_id": row.actor_id,
            "created_at": row.occurred_at, **_payload(row),
        } for row in events],
        "history_limited": True, "original_source_preserved": True,
        "paid_provider_called": False,
    }
