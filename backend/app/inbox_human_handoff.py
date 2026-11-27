"""v186.3: scoped officer-feedback governance and read-only Gate 2 handoff readiness.

Information QA is NOT legal verification. A feedback triage decision is NOT
model training or model-promotion approval. No insight proposal/publishing APIs
are called here. Uses existing append-only AuditEvent records, no new schema.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .access import has
from .auth import current_user
from .db import get_db
from .models import AuditEvent, EvidenceAssessment, SocialListeningResult, User
from .governance_persistence import _campaign, _grant, _source
from .inbox_gate_integrity import GATE1_AUDIT_SUBJECT, audit_payload, review_projection, source_integrity_digest
from .inbox_human_gate import _read_enabled
from .inbox_gate_real_qa_v1867 import (QA_ID,QA_ACTIONS,projection,reviewed_state,is_qa_campaign)
from .inbox_human_corrections import (
    _latest_assessment, _latest_sentiment, _latest_decision, _lock_current_source,
    _authorize, can_edit_gate1, is_pilot_qa_source,
)

router = APIRouter(prefix="/api/inbox/human-review", tags=["inbox-human-review"])

FEEDBACK_SUBJECT = "Gate1FeedbackDecision"
CORRECTION_ACTIONS = QA_ACTIONS
TRIAGE = frozenset(("ACCEPT_OFFLINE_EVALUATION", "REJECT_OFFLINE_EVALUATION", "NEEDS_RECHECK"))
MAX_FEEDBACK_SCAN = 200
MAX_FEEDBACK_PAGE = 40


class FeedbackTriageIn(BaseModel):
    correction_event_id: int = Field(gt=0)
    expected_decision_revision: int = Field(ge=0)
    decision: str
    rationale: str = Field(min_length=10, max_length=1500)
    expected_source_digest: str = Field(min_length=64, max_length=64)


def _feedback_decision_subject(campaign_id, result_id, event_id):
    return f"{campaign_id}:{result_id}:{event_id}"


def _latest_triage(db, campaign_id, result_id, event_id):
    return (db.query(AuditEvent)
            .filter_by(subject_type=FEEDBACK_SUBJECT,
                       subject_id=_feedback_decision_subject(campaign_id, result_id, event_id),
                       action="GATE1_FEEDBACK_TRIAGED")
            .order_by(AuditEvent.id.desc()).first())


def _feedback_event(db, campaign_id, result_id, event_id):
    row = db.get(AuditEvent, event_id)
    if not (row and row.subject_type == GATE1_AUDIT_SUBJECT
            and row.subject_id == f"{campaign_id}:{result_id}"
            and row.action in CORRECTION_ACTIONS):
        raise HTTPException(404, "Correction feedback unavailable")
    payload = audit_payload(row)
    if payload.get("qa_audit_only"):
        payload["correction_id"]=row.id
    if payload.get("campaign_id") != campaign_id or payload.get("result_id") != result_id:
        raise HTTPException(404, "Correction feedback unavailable")
    return row, payload


def _review_current(db, campaign_id, result_id, source, assessment=None, sentiment=None):
    if assessment is None:
        assessment = _latest_assessment(db, campaign_id, result_id)
    if sentiment is None:
        sentiment = _latest_sentiment(db, campaign_id, result_id)
    state=review_projection(
        _latest_decision(db, campaign_id, result_id),
        assessment, sentiment, source,
    )
    return reviewed_state(db,campaign_id,result_id,assessment,sentiment,source,state)


def _correction_current(payload, assessment, sentiment, source, db=None, campaign_id=None, result_id=None):
    field = payload.get("field_name")
    revision = payload.get("correction_id")
    if payload.get("qa_audit_only"):
        if db is None or campaign_id!=QA_ID:return False
        qa=projection(db,campaign_id,result_id,assessment,sentiment,source)
        return bool(revision and revision>0
                    and qa.get(f"qa_{field}_event")==revision
                    and not qa["qa_stale"])
    if field == "relevance":
        current = assessment is not None and assessment.id == revision
    elif field == "sentiment":
        current = sentiment is not None and sentiment.id == revision
    else:
        current = False
    return bool(current and payload.get("source_integrity_digest") ==
                source_integrity_digest(source))


def _feedback_view(db, campaign_id, result_id, event, source, assessment=None, sentiment=None):
    payload = audit_payload(event)
    if payload.get("qa_audit_only"):
        payload["correction_id"]=event.id
    assessment = assessment or _latest_assessment(db, campaign_id, result_id)
    sentiment = sentiment or _latest_sentiment(db, campaign_id, result_id)
    review = _review_current(db, campaign_id, result_id, source, assessment, sentiment)
    current = _correction_current(payload, assessment, sentiment, source, db,campaign_id,result_id)
    triage = _latest_triage(db, campaign_id, result_id, event.id)
    decision = audit_payload(triage) if triage else {}
    # An approved feedback example becomes stale after a later field/source
    # revision or if the information review is no longer current.
    accepted = bool(decision.get("decision") == "ACCEPT_OFFLINE_EVALUATION"
                    and current
                    and review["information_review_status"] == "OFFICER_VERIFIED")
    return {
        "correction_event_id": event.id,
        "campaign_id": str(campaign_id),
        "result_id": str(result_id),
        "field": payload.get("field_name"),
        "previous_effective_value": payload.get("old_effective_value"),
        "officer_value": payload.get("new_effective_value"),
        "reason": payload.get("reason"),
        "officer_id": event.actor_id,
        "corrected_at": event.occurred_at,
        "correction_current": current,
        "information_review_status": review["information_review_status"],
        "triage_decision": decision.get("decision", "UNREVIEWED"),
        "triage_revision": triage.id if triage else 0,
        "triaged_by": triage.actor_id if triage else None,
        "triage_reason": decision.get("rationale"),
        "offline_evaluation_candidate": accepted,
        "training_approved": False,
        "training_triggered": False,
        "model_promotion_approved": False,
    }


def _can_triage(officer, campaign, source):
    return bool(has(officer, "administration")
                and has(officer, "human_validation")
                and can_edit_gate1(officer, campaign)
                and (is_pilot_qa_source(source) or is_qa_campaign(campaign)))


@router.get("/campaign/{campaign_id}/source/{result_id}/feedback")
def source_feedback(campaign_id: int, result_id: int,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    _read_enabled()
    officer = _grant(db, user, "view_intelligence")
    campaign = _campaign(db, officer, campaign_id)
    source = _source(db, officer, campaign_id, result_id)
    assessment = _latest_assessment(db, campaign_id, result_id)
    sentiment = _latest_sentiment(db, campaign_id, result_id)
    rows = (db.query(AuditEvent)
            .filter_by(subject_type=GATE1_AUDIT_SUBJECT,
                       subject_id=f"{campaign_id}:{result_id}")
            .filter(AuditEvent.action.in_(CORRECTION_ACTIONS))
            .order_by(AuditEvent.id.desc()).limit(MAX_FEEDBACK_PAGE).all())
    return {
        "items": [_feedback_view(db, campaign_id, result_id, event, source, assessment, sentiment)
                  for event in rows],
        "can_triage": _can_triage(officer, campaign, source),
        "history_limited": True, "training_enabled": False,
        "automatic_training": False, "automatic_publication": False,
    }


@router.get("/campaign/{campaign_id}/feedback")
def campaign_feedback(campaign_id: int, cursor: int | None = None,
                      limit: int = 20, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    _read_enabled()
    officer = _grant(db, user, "view_intelligence")
    _campaign(db, officer, campaign_id)
    if not 1 <= limit <= MAX_FEEDBACK_PAGE or (cursor is not None and cursor <= 0):
        raise HTTPException(422, "Invalid feedback page")
    query = (db.query(AuditEvent)
             .filter_by(subject_type=GATE1_AUDIT_SUBJECT)
             .filter(AuditEvent.action.in_(CORRECTION_ACTIONS))
             .filter(AuditEvent.subject_id.like(f"{campaign_id}:%")))
    if cursor:
        query = query.filter(AuditEvent.id < cursor)
    rows = query.order_by(AuditEvent.id.desc()).limit(MAX_FEEDBACK_SCAN).all()
    items = []
    last_scanned = None
    for event in rows:
        last_scanned = event.id
        parts = event.subject_id.split(":")
        if len(parts) != 2 or parts[0] != str(campaign_id) or not parts[1].isdecimal():
            continue
        result_id = int(parts[1])
        try:
            source = _source(db, officer, campaign_id, result_id)
        except HTTPException:
            # Do not disclose out-of-scope source identifiers.
            continue
        items.append(_feedback_view(db, campaign_id, result_id, event, source))
        if len(items) >= limit:
            break
    has_more = bool(last_scanned is not None and db.query(AuditEvent.id).filter(
        AuditEvent.subject_type == GATE1_AUDIT_SUBJECT,
        AuditEvent.action.in_(CORRECTION_ACTIONS),
        AuditEvent.subject_id.like(f"{campaign_id}:%"),
        AuditEvent.id < last_scanned,
    ).first())
    return {
        "items": items,
        "next_cursor": last_scanned if has_more else None,
        "has_more": has_more,
        "scan_limited": bool(has_more and len(rows) >= MAX_FEEDBACK_SCAN),
        "page_count": len(items),
        "not_population_totals": True,
        "training_enabled": False,
        "automatic_publication": False,
    }


@router.post("/campaign/{campaign_id}/source/{result_id}/feedback/triage")
def triage_feedback(campaign_id: int, result_id: int, body: FeedbackTriageIn,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    officer, campaign, source = _authorize(db, user, campaign_id, result_id, True)
    if not _can_triage(officer, campaign, source):
        raise HTTPException(403, "Synthetic pilot administrator authorization required")
    decision = body.decision.strip().upper()
    if decision not in TRIAGE:
        raise HTTPException(422, "Invalid offline feedback decision")
    # Under the same source-row lock used by field corrections and review
    # decisions, reject stale form revisions, source changes and labels.
    source = _lock_current_source(db, officer, source)
    if source_integrity_digest(source) != body.expected_source_digest:
        raise HTTPException(409, "Original source changed; refresh before triage")
    event, payload = _feedback_event(db, campaign_id, result_id, body.correction_event_id)
    assessment = _latest_assessment(db, campaign_id, result_id)
    sentiment = _latest_sentiment(db, campaign_id, result_id)
    latest = _latest_triage(db, campaign_id, result_id, event.id)
    if (latest.id if latest else 0) != body.expected_decision_revision:
        raise HTTPException(409, "Offline feedback triage changed; refresh")
    if decision == "ACCEPT_OFFLINE_EVALUATION":
        if not _correction_current(payload, assessment, sentiment, source, db,campaign_id,result_id):
            raise HTTPException(409, "Correction is no longer effective; recheck before acceptance")
        review = _review_current(db, campaign_id, result_id, source, assessment, sentiment)
        if review["information_review_status"] != "OFFICER_VERIFIED":
            raise HTTPException(409, "A current Gate 1 information review is required")
    row = AuditEvent(
        subject_type=FEEDBACK_SUBJECT,
        subject_id=_feedback_decision_subject(campaign_id, result_id, event.id),
        action="GATE1_FEEDBACK_TRIAGED",
        actor_id=str(user.id), actor_name=str(officer.get("name") or "")[:255],
        changes_json=json.dumps({
            "campaign_id": campaign_id, "result_id": result_id,
            "correction_event_id": event.id,
            "decision": decision, "rationale": body.rationale.strip(),
            "previous_triage_revision": latest.id if latest else 0,
            "source_integrity_digest": source_integrity_digest(source),
            "assessment_id": assessment.id if assessment else None,
            "sentiment_revision": sentiment.id if sentiment else None,
            "officer_id": event.actor_id,
            "training_approved": False, "training_triggered": False,
            "model_promotion_approved": False,
            "official_insight_published": False,
        }, ensure_ascii=False, sort_keys=True),
        occurred_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(row)
    db.commit()
    return {
        "saved": True, "decision": decision, "triage_revision": row.id,
        "automatic_training": False, "training_approved": False,
        "automatic_publication": False,
    }


@router.get("/campaign/{campaign_id}/source/{result_id}/gate2-readiness")
def gate2_handoff_preview(campaign_id: int, result_id: int,
                          user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Information-only handoff preview, never a proposed/published insight."""
    _read_enabled()
    officer = _grant(db, user, "view_intelligence")
    _campaign(db, officer, campaign_id)
    source = _source(db, officer, campaign_id, result_id)
    assessment = _latest_assessment(db, campaign_id, result_id)
    sentiment = _latest_sentiment(db, campaign_id, result_id)
    review = _review_current(db, campaign_id, result_id, source, assessment, sentiment)
    qa=projection(db,campaign_id,result_id,assessment,sentiment,source)
    label=str(qa["effective_relevance"] or "UNASSESSED").upper()
    blockers = []
    if campaign_id==QA_ID:
        blockers.append("QA_CAMPAIGN_NOT_ELIGIBLE_FOR_PUBLICATION")
        if qa["qa_stale"]:blockers.append("QA_CORRECTION_REVALIDATION_REQUIRED")
    if assessment is None or label in ("", "UNASSESSED") or (
        assessment and assessment.model_version == "PRISM_PENDING_OPENAI"
    ):
        blockers.append("SAVED_ASSESSMENT_REQUIRED")
    if label not in ("RELEVANT", "HIGHLY_RELEVANT"):
        blockers.append("ELECTION_RELEVANCE_NOT_CONFIRMED")
    if not (source.text_content or source.canonical_url):
        blockers.append("SOURCE_TRACE_REQUIRED")
    if review["information_review_status"] != "OFFICER_VERIFIED":
        blockers.append("CURRENT_GATE1_INFORMATION_REVIEW_REQUIRED")
    # Check legacy governance ledger for conflicting human sentiment values.
    from .governance_persistence import _sentiment_review_conflicts
    if _sentiment_review_conflicts(db, campaign_id, [result_id]):
        blockers.append("REVIEW_LEDGER_CONFLICT")
    return {
        "campaign_id": str(campaign_id),
        "result_id": str(result_id),
        "gate1_review_status": review["information_review_status"],
        "effective_relevance": label,
        "effective_sentiment":qa["effective_sentiment"],
        "assessment_id": assessment.id if assessment else None,
        "assessment_version": assessment.assessment_version if assessment else None,
        "officer_sentiment_revision": sentiment.id if sentiment else 0,
        "information_review_revision": review["information_review_revision"],
        "source_integrity_digest": source_integrity_digest(source),
        "readiness": "CANDIDATE_FOR_INSIGHT_DRAFT" if not blockers else "BLOCKED",
        "review_blockers": blockers,
        "claim_status": "preliminary",
        "legal_allegations_verified": False,
        "evidence_legally_verified": False,
        "proposed_insight_created": False,
        "gate2_independent_approval_required": True,
        "command_centre_published": False,
        "model_training_triggered": False,
        "paid_provider_called": False,
    }
