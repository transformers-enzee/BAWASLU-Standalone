"""Read-only, source-scoped Gate 1 evidence QA for BAWASLU administrators.

Sample intentionally includes uncertain, excluded and unassessed election
discussion; it is not a violation-only queue or a whole-dataset statistic.
No mutations, paid AI calls, raw social text, or external provider requests.
"""
from collections import Counter
from sqlalchemy import func
from sqlalchemy.orm import defer
from .models import CampaignEvidence, SocialListeningResult, EvidenceAssessment, EvidenceReview
from .officer_sentiment import OfficerSentimentCorrection
from .socialcrawl import _result_in_scope

SCAN_LIMIT = 120
DISPLAY_LIMIT = 20
RELEVANT = {"RELEVANT", "HIGHLY_RELEVANT"}
EXCLUDED = {"IRRELEVANT", "UNCERTAIN"}


def classify_information(assessment, sentiment_correction=None, review=None):
    """Separate evidence classification quality from possible rule violations."""
    label = str(getattr(assessment, "relevance_label", "") or "UNASSESSED").upper()
    preliminary = bool(assessment and assessment.model_version == "PRISM_PENDING_OPENAI")
    if assessment is None or preliminary or label == "UNASSESSED":
        category, action = "unassessed", "VERIFY_UNASSESSED"
    elif label == "UNCERTAIN":
        category, action = "excluded_or_uncertain", "REVIEW_UNCERTAIN"
    elif label == "IRRELEVANT":
        category, action = "excluded_or_uncertain", "SPOT_CHECK_EXCLUDED"
    elif label in RELEVANT:
        category, action = "relevant", "CHECK_RELEVANT_EVIDENCE"
    else:
        category, action = "other", "REVIEW_UNKNOWN_LABEL"
    ai_sentiment = str(getattr(assessment, "sentiment", "") or "UNKNOWN").upper()
    officer_sentiment = getattr(sentiment_correction, "sentiment", None)
    return {
        "category": category,
        "action": action,
        "relevance": label if not preliminary else "UNASSESSED",
        "relevance_confidence": str(getattr(assessment, "relevance_confidence", "") or ""),
        "ai_sentiment": ai_sentiment,
        "effective_sentiment": str(officer_sentiment or ai_sentiment).upper(),
        "sentiment_basis": "OFFICER_CORRECTION" if officer_sentiment else "SAVED_ASSESSMENT",
        "officer_review_decision": getattr(review, "decision", None),
        "review_recorded": review is not None,
        "assessment_version": getattr(assessment, "assessment_version", None),
    }


def _latest_per_source(db, model, campaign_id, source_ids, id_key):
    """Bounded, cross-database latest-row selection without per-source queries."""
    rank = (db.query(
        model.id.label("record_id"),
        func.row_number().over(
            partition_by=(model.campaign_id, model.result_id),
            order_by=(
                (model.assessment_version.desc(), model.id.desc())
                if model is EvidenceAssessment else model.id.desc()
            )
        ).label("position"))
        .filter(model.campaign_id == campaign_id, model.result_id.in_(source_ids))
        .subquery())
    return {
        getattr(row, id_key):row for row in
        db.query(model).join(rank,model.id==rank.c.record_id)
        .filter(rank.c.position==1).all()
    }


def information_qa_sample(db, officer_profile, campaign_id):
    """Return a labeled recent-link sample, not complete campaign-wide metrics."""
    links = (
        db.query(CampaignEvidence)
        .filter(CampaignEvidence.campaign_id==campaign_id,
                CampaignEvidence.match_method!="WATCHLIST_ACCOUNT")
        .order_by(CampaignEvidence.id.desc())
        .limit(SCAN_LIMIT + 1).all()
    )
    truncated = len(links)>SCAN_LIMIT
    links = links[:SCAN_LIMIT]
    source_ids = list(dict.fromkeys(link.result_id for link in links))
    if not source_ids:
        return {
            "scanned_count":0,"counts":{"unassessed":0,"excluded_or_uncertain":0,
                                        "relevant":0,"other":0},
            "items":[],"sample_limit":DISPLAY_LIMIT,"scan_limit":SCAN_LIMIT,
            "sample_truncated":False,"not_population_totals":True,
            "watchlist_links_excluded":True,"paid_provider_called":False,
        }
    posts={
        row.id:row for row in db.query(SocialListeningResult)
        .options(defer(SocialListeningResult.raw_payload_json))
        .filter(SocialListeningResult.id.in_(source_ids)).all()
    }
    scoped_ids=[
        source_id for source_id in source_ids
        if source_id in posts and _result_in_scope(db,officer_profile,posts[source_id])
    ]
    if not scoped_ids:
        return {
            "scanned_count":0,"counts":{"unassessed":0,"excluded_or_uncertain":0,
                                        "relevant":0,"other":0},
            "items":[],"sample_limit":DISPLAY_LIMIT,"scan_limit":SCAN_LIMIT,
            "sample_truncated":truncated,"not_population_totals":True,
            "watchlist_links_excluded":True,"paid_provider_called":False,
        }
    assessments=_latest_per_source(
        db,EvidenceAssessment,campaign_id,scoped_ids,"result_id")
    sentiments=_latest_per_source(
        db,OfficerSentimentCorrection,campaign_id,scoped_ids,"result_id")
    assessment_ids=[a.id for a in assessments.values()]
    reviews={}
    if assessment_ids:
        ranked = (
            db.query(
                EvidenceReview.id.label("record_id"),
                func.row_number().over(
                    partition_by=EvidenceReview.assessment_id,
                    order_by=(EvidenceReview.created_at.desc(),EvidenceReview.id.desc())
                ).label("position")
            )
            .filter(EvidenceReview.assessment_id.in_(assessment_ids))
            .subquery()
        )
        reviews={
            row.assessment_id:row for row in
            db.query(EvidenceReview).join(ranked,EvidenceReview.id==ranked.c.record_id)
            .filter(ranked.c.position==1).all()
        }
    all_items=[]
    for source_id in scoped_ids:
        assessment=assessments.get(source_id)
        classification=classify_information(
            assessment, sentiments.get(source_id),
            reviews.get(assessment.id) if assessment else None
        )
        all_items.append({
            "result_id":str(source_id),"campaign_id":str(campaign_id),
            "platform":posts[source_id].platform or "",
            "published_at":posts[source_id].published_at or "",
            **classification,
        })
    counts=Counter(item["category"] for item in all_items)
    priority={"VERIFY_UNASSESSED":0,"REVIEW_UNCERTAIN":1,
              "SPOT_CHECK_EXCLUDED":2,"REVIEW_UNKNOWN_LABEL":3,
              "CHECK_RELEVANT_EVIDENCE":4}
    # Original link order is newest first; stable priority ensures false-negative
    # samples are visible instead of only already-relevant posts.
    selected=sorted(all_items,key=lambda item:priority.get(item["action"],5))[:DISPLAY_LIMIT]
    return {
        "scanned_count":len(all_items),
        "counts":{k:counts.get(k,0) for k in
                  ("unassessed","excluded_or_uncertain","relevant","other")},
        "items":selected,"sample_limit":DISPLAY_LIMIT,"scan_limit":SCAN_LIMIT,
        "sample_truncated":truncated or len(all_items)>DISPLAY_LIMIT,
        "not_population_totals":True,"watchlist_links_excluded":True,
        "paid_provider_called":False,
    }
