"""Gate 1 read-only integrity projection shared by source detail and paginated queue.

This projection is deliberately not a legal-fact validator. A review can only
certify that an officer reviewed the current saved information snapshot.
"""
import hashlib
import json

GATE1_AUDIT_SUBJECT = "Gate1InformationReview"
VALID_REVIEW_STATES = frozenset(("OFFICER_VERIFIED", "NEEDS_REVIEW", "HELD", "EXCLUDED"))
STATUS_FILTERS = frozenset(("all", "needs_review", "officer_verified", "held", "excluded",
                             "revalidation_required"))
INFORMATION_SOURCE_FIELDS = (
    "id", "run_id", "provider", "provider_result_id", "platform",
    "canonical_url", "author_name", "published_at", "text_content",
    "content_fingerprint",
)


def source_integrity_digest(source):
    """Hash saved source identity/content; never return source text in audit logs."""
    if source is None:
        return None
    snapshot = {field: getattr(source, field, None) for field in INFORMATION_SOURCE_FIELDS}
    return hashlib.sha256(json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, default=str,
    ).encode("utf-8")).hexdigest()


def audit_payload(event):
    if event is None:
        return {}
    try:
        result = json.loads(event.changes_json or "{}")
    except (TypeError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


def review_projection(event, assessment, sentiment, source):
    """Review becomes stale after a changed assessment, correction or source.

    Older v185.8 review events missing a source digest fail closed as stale.
    No new write is performed when an event becomes stale.
    """
    digest = source_integrity_digest(source)
    base = {
        "information_review_status": "NEEDS_REVIEW",
        "information_review_revision": 0,
        "information_review_reviewer_id": None,
        "information_review_reason": None,
        "information_review_at": None,
        "information_review_stale": False,
        "source_integrity_digest": digest,
    }
    if event is None:
        return base
    fields = audit_payload(event)
    assessment_id = assessment.id if assessment is not None else None
    sentiment_id = sentiment.id if sentiment is not None else None
    stale = (
        fields.get("assessment_id") != assessment_id
        or fields.get("sentiment_correction_id") != sentiment_id
        or fields.get("source_integrity_digest") != digest
    )
    base.update({
        "information_review_status": "REVALIDATION_REQUIRED" if stale
                                     else fields.get("status", "NEEDS_REVIEW"),
        "information_review_revision": event.id,
        "information_review_reviewer_id": event.actor_id,
        "information_review_reason": fields.get("reason"),
        "information_review_at": event.occurred_at,
        "information_review_stale": stale,
    })
    return base


def review_status_matches(record, status_filter):
    if status_filter == "all":
        return True
    return record.get("information_review_status", "").lower() == status_filter


def saved_relevance_basis(assessment):
    return "OFFICER_CORRECTION" if (
        assessment is not None and assessment.model_version == "HUMAN_OVERRIDE"
    ) else "SAVED_ASSESSMENT" if assessment is not None else "UNASSESSED"
