"""Read-only, cursor-paginated officer Gate 1 queue (v185.7).

This is distinct from the deliberately balanced, bounded administrator QA sample.
Every returned source is linked to the authorized campaign and checked against
the officer's geographic source scope. No population totals, mutations or AI calls.
"""
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import defer

from .governance_information_qa import _latest_per_source, classify_information
from .models import CampaignEvidence, EvidenceAssessment, EvidenceReview, SocialListeningResult, AuditEvent
from .officer_sentiment import OfficerSentimentCorrection
from .socialcrawl import _result_in_scope
from .inbox_gate_integrity import (
    GATE1_AUDIT_SUBJECT, STATUS_FILTERS, review_projection,
    review_status_matches, saved_relevance_basis,
)

DEFAULT_PAGE_SIZE = 40
MAX_PAGE_SIZE = 100
FETCH_BATCH = 200
MAX_SCAN_PER_REQUEST = 2000
CATEGORIES = frozenset({"all", "unassessed", "uncertain", "excluded", "relevant", "other"})
CATEGORY_ACTIONS = {
    "unassessed": frozenset({"VERIFY_UNASSESSED"}),
    "uncertain": frozenset({"REVIEW_UNCERTAIN"}),
    "excluded": frozenset({"SPOT_CHECK_EXCLUDED"}),
    "relevant": frozenset({"CHECK_RELEVANT_EVIDENCE"}),
    "other": frozenset({"REVIEW_UNKNOWN_LABEL"}),
}


def _classified_batch(db, officer, campaign_id, links):
    """Classify a bounded link batch without querying assessments per source."""
    ids = list(dict.fromkeys(link.result_id for link in links))
    if not ids:
        return {}
    sources = {
        item.id: item for item in db.query(SocialListeningResult)
        .options(defer(SocialListeningResult.raw_payload_json))
        .filter(SocialListeningResult.id.in_(ids)).all()
    }
    scoped = [sid for sid in ids if sid in sources and
              _result_in_scope(db, officer, sources[sid])]
    if not scoped:
        return {}
    assessments = _latest_per_source(db, EvidenceAssessment, campaign_id, scoped, "result_id")
    sentiment = _latest_per_source(db, OfficerSentimentCorrection, campaign_id, scoped, "result_id")
    assessment_ids = [row.id for row in assessments.values()]
    reviews = {}
    if assessment_ids:
        ranked = (db.query(
            EvidenceReview.id.label("record_id"),
            func.row_number().over(
                partition_by=EvidenceReview.assessment_id,
                order_by=(EvidenceReview.created_at.desc(), EvidenceReview.id.desc())
            ).label("position"))
            .filter(EvidenceReview.assessment_id.in_(assessment_ids))
            .subquery())
        reviews = {
            row.assessment_id: row for row in
            db.query(EvidenceReview).join(ranked, EvidenceReview.id == ranked.c.record_id)
            .filter(ranked.c.position == 1).all()
        }
    # A single scoped audit query provides latest record-level QA states without
    # per-post round trips. Stale decisions are flagged after any field change.
    names = [f"{campaign_id}:{sid}" for sid in scoped]
    ranked_decisions = (db.query(
        AuditEvent.id.label("event_id"),
        func.row_number().over(
            partition_by=AuditEvent.subject_id,
            order_by=AuditEvent.id.desc()
        ).label("position"))
        .filter(AuditEvent.subject_type == GATE1_AUDIT_SUBJECT,
                AuditEvent.action == "GATE1_INFORMATION_DECISION",
                AuditEvent.subject_id.in_(names))
        .subquery())
    decision_rows = (db.query(AuditEvent)
        .join(ranked_decisions, AuditEvent.id == ranked_decisions.c.event_id)
        .filter(ranked_decisions.c.position == 1).all())
    decision_by_source = {int(row.subject_id.split(":")[-1]): row for row in decision_rows}
    results = {}
    for sid in scoped:
        assessment = assessments.get(sid)
        label = classify_information(
            assessment, sentiment.get(sid),
            reviews.get(assessment.id) if assessment else None
        )
        state = review_projection(decision_by_source.get(sid), assessment,
                                  sentiment.get(sid), sources[sid])
        # Source digest is supplied only when opening evidence details;
        # the queue needs only review status, not an integrity token.
        state.pop("source_integrity_digest", None)
        results[sid] = {
            **state,
            "relevance_basis": saved_relevance_basis(assessment),
            "campaign_id": str(campaign_id),
            "result_id": str(sid),
            "platform": sources[sid].platform or "",
            "published_at": sources[sid].published_at or "",
            **label,
        }
    return results


def paginated_review_queue(db, officer, campaign_id, page_size=DEFAULT_PAGE_SIZE,
                           cursor=None, category="all", review_status="all"):
    """Keyset pagination through ALL ordinary campaign links, not latest 120.

    Processing is capped per HTTP request for safety; a continuation cursor
    allows a subsequent request to resume without silently dropping entries.
    A page may be empty but continuable when geography or category filters
    eliminate a scanned segment. Counts describe returned page items only.
    """
    if category not in CATEGORIES:
        raise HTTPException(422, "Unsupported review category")
    if review_status not in STATUS_FILTERS:
        raise HTTPException(422, "Unsupported information QA status")
    if not isinstance(page_size, int) or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise HTTPException(422, "page_size must be between 1 and 100")
    if cursor is not None and (not isinstance(cursor, int) or cursor <= 0):
        raise HTTPException(422, "Invalid review cursor")
    selected = []
    position = cursor
    scanned = 0
    exhausted = False
    while len(selected) < page_size and scanned < MAX_SCAN_PER_REQUEST:
        batch_size = min(FETCH_BATCH, MAX_SCAN_PER_REQUEST - scanned)
        query = db.query(CampaignEvidence).filter(
            CampaignEvidence.campaign_id == campaign_id,
            CampaignEvidence.match_method != "WATCHLIST_ACCOUNT"
        )
        if position is not None:
            query = query.filter(CampaignEvidence.id < position)
        links = query.order_by(CampaignEvidence.id.desc()).limit(batch_size).all()
        if not links:
            exhausted = True
            break
        labels = _classified_batch(db, officer, campaign_id, links)
        scanned += len(links)
        for link in links:
            position = link.id  # advance only over examined links, never whole batch
            entry = labels.get(link.result_id)
            if entry is None:
                continue
            if category != "all" and entry["action"] not in CATEGORY_ACTIONS[category]:
                continue
            if not review_status_matches(entry, review_status):
                continue
            selected.append(entry)
            if len(selected) >= page_size:
                break
        if len(selected) >= page_size:
            break
        if len(links) < batch_size:
            exhausted = True
            break

    # Peek only for existence of another campaign link; never claim a full
    # scoped count, or expose an out-of-scope source from this check.
    has_more = False
    if not exhausted and position is not None:
        has_more = db.query(CampaignEvidence.id).filter(
            CampaignEvidence.campaign_id == campaign_id,
            CampaignEvidence.match_method != "WATCHLIST_ACCOUNT",
            CampaignEvidence.id < position,
        ).first() is not None
    counts = Counter(item["category"] for item in selected)
    review_counts = Counter(item.get("information_review_status", "NEEDS_REVIEW") for item in selected)
    return {
        "campaign_id": str(campaign_id),
        "queue_name": "NEEDS_HUMAN_REVIEW",
        "items": selected,
        "page_count": len(selected),
        "page_counts": {key: counts.get(key, 0) for key in
                        ("unassessed", "excluded_or_uncertain", "relevant", "other")},
        "page_review_status_counts": {key: review_counts.get(key, 0) for key in
                                    ("NEEDS_REVIEW", "OFFICER_VERIFIED", "HELD",
                                     "EXCLUDED", "REVALIDATION_REQUIRED")},
        "next_cursor": str(position) if has_more else None,
        "has_more": has_more,
        "scan_limited": bool(has_more and scanned >= MAX_SCAN_PER_REQUEST),
        "filter_category": category,
        "filter_review_status": review_status,
        "page_size": page_size,
        "count_is_page_only": True,
        "not_population_totals": True,
        "watchlist_links_excluded": True,
        "separate_from_standard_inbox": True,
        "no_automatic_publication": True,
        "paid_provider_called": False,
    }
