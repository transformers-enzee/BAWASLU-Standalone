"""Officer Human Gate 1 within the existing Intelligence Inbox.

Read-only sources and sample, scoped by campaign AND geographic assignment.
Independent feature flags allow verification without affecting the ordinary
relevant-only Inbox feed, existing aggregates, or governance publication.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .access import allowed, has
from .models import (
    User, MonitoringCampaign, EvidenceAssessment, EvidenceReview
)
from .officer_sentiment import OfficerSentimentCorrection
from .governance_persistence import _grant, _campaign, _source
from .governance_information_qa import information_qa_sample, classify_information
from .inbox_human_queue import paginated_review_queue
from .inbox_gate_real_qa_v1867 import (is_qa_campaign,isolated_source,projection)

router=APIRouter(prefix="/api/inbox/human-review",tags=["inbox-human-review"])


def _read_enabled():
    if os.getenv("BAWASLU_INBOX_GATE1_READ_ENABLED","").strip().lower() not in ("1","true","yes"):
        raise HTTPException(503,"Inbox Human Review is not yet enabled")


def _write_enabled():
    return os.getenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","").strip().lower() in ("1","true","yes")


@router.get("/campaigns")
def review_campaigns(user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Only campaigns already visible to the current officer."""
    _read_enabled()
    officer=_grant(db,user,"view_intelligence")
    candidates=db.query(MonitoringCampaign).order_by(MonitoringCampaign.id.desc()).limit(1000).all()
    scoped=[{"id":str(row.id),"name":row.name,
             "province":row.province or "","regency_city":row.regency_city or ""}
            for row in candidates if allowed(officer,row)]
    return {"campaigns":scoped[:100],"truncated":len(scoped)>100 or len(candidates)>=1000,
            "read_only":not _write_enabled(),"paid_provider_called":False}


@router.get("/campaign/{campaign_id}/sample")
def review_sample(campaign_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Balanced QA sample; not total eligible posts, not legal violation counts."""
    _read_enabled()
    officer=_grant(db,user,"view_intelligence")
    _campaign(db,officer,campaign_id)
    sample=information_qa_sample(db,officer,campaign_id)
    return {"campaign_id":str(campaign_id),**sample,
            "queue_name":"NEEDS_HUMAN_REVIEW",
            "separate_from_standard_inbox":True,
            "no_automatic_publication":True}


@router.get("/campaign/{campaign_id}/source/{result_id}")
def review_source(campaign_id:int,result_id:int,user:User=Depends(current_user),
                  db:Session=Depends(get_db)):
    """Open any authorized ordinary campaign evidence, even if AI excluded it.

    This must not rely on the normal Inbox relevant-only eligibility filter.
    """
    _read_enabled()
    officer=_grant(db,user,"view_intelligence")
    campaign=_campaign(db,officer,campaign_id)
    source=_source(db,officer,campaign_id,result_id)
    assessment=(db.query(EvidenceAssessment)
                .filter_by(campaign_id=campaign_id,result_id=result_id)
                .order_by(EvidenceAssessment.assessment_version.desc(),
                          EvidenceAssessment.id.desc()).first())
    sentiment=(db.query(OfficerSentimentCorrection)
               .filter_by(campaign_id=campaign_id,result_id=result_id)
               .order_by(OfficerSentimentCorrection.id.desc()).first())
    review=None
    if assessment is not None:
        review=(db.query(EvidenceReview).filter_by(assessment_id=assessment.id)
                .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).first())
    classification=classify_information(assessment,sentiment,review)
    from .inbox_human_corrections import (
        can_edit_gate1, is_pilot_qa_source, review_state_for_source,
    )
    from .inbox_gate_integrity import saved_relevance_basis
    # Preserve a visible distinction between the original AI label and the
    # current effective label after append-only officer correction.
    ai_baseline=assessment
    if assessment is not None and assessment.model_version=="HUMAN_OVERRIDE":
        ai_baseline=(db.query(EvidenceAssessment)
                     .filter_by(campaign_id=campaign_id,result_id=result_id)
                     .filter(EvidenceAssessment.model_version!="HUMAN_OVERRIDE")
                     .order_by(EvidenceAssessment.assessment_version.desc(),
                               EvidenceAssessment.id.desc()).first())
    can_write=bool(can_edit_gate1(officer,campaign) and
                   (is_pilot_qa_source(source) and not is_qa_campaign(campaign)
                    or isolated_source(db,campaign,source)))
    can_correct=bool(can_write and assessment is not None)
    state=review_state_for_source(db,campaign_id,result_id,assessment,sentiment,source)
    qa=projection(db,campaign_id,result_id,assessment,sentiment,source)
    from .inbox_human_full_review_v1868 import full_projection
    enrichment=full_projection(db,campaign_id,result_id,assessment,source) if is_qa_campaign(campaign) else None
    original_text=source.text_content or ""
    return {
        "campaign_id":str(campaign_id),"campaign_name":campaign.name,
        "result_id":str(source.id),"platform":source.platform or "",
        "author_name":source.author_name or "",
        "published_at":source.published_at or "",
        "canonical_url":source.canonical_url or "",
        "text_content":original_text[:20000],
        "content_truncated":len(original_text)>20000,
        "assessment_id":assessment.id if assessment else None,
        "model_version":assessment.model_version if assessment else None,
        "assessment_version":assessment.assessment_version if assessment else None,
        "original_ai_relevance":ai_baseline.relevance_label if ai_baseline else None,
        "effective_relevance":qa["effective_relevance"],
        "relevance_basis":qa["relevance_basis"] if is_qa_campaign(campaign) else saved_relevance_basis(assessment),
        "relevance_explanation":assessment.explanation if assessment else "",
        "sentiment_explanation":assessment.sentiment_explanation if assessment else "",
        **classification,
        "effective_sentiment":qa["effective_sentiment"] if is_qa_campaign(campaign) else classification["effective_sentiment"],
        "sentiment_basis":qa["sentiment_basis"] if is_qa_campaign(campaign) else classification["sentiment_basis"],
        "qa_audit_only":is_qa_campaign(campaign),
        "full_field_revision":enrichment["revision"] if enrichment else 0,
        "full_field_stale":enrichment["stale"] if enrichment else False,
        "full_field_secondary_review":enrichment["secondary_review"]["status"] if enrichment else "NOT_REQUIRED",
        "can_correct_relevance":can_correct,
        "can_correct_sentiment":can_correct,
        "can_review_information":can_write,
        "relevance_revision":qa["relevance_revision"],
        "sentiment_revision":qa["sentiment_revision"],
        **state,
        "read_only":not can_write,
        "review_action_available":assessment is not None,
        "reason_if_not_actionable":(
            "A saved assessment is required before the existing officer correction workflow can be used."
            if assessment is None else
            "Human Review corrections are not enabled for this officer or pilot."
            if not can_correct else ""
        ),
        "legacy_correction_path":True,
        "gate1_correction_audit_available":True,
        "original_source_preserved":True,
        "official_insight_approval_required":True,
        "paid_provider_called":False,
    }


@router.get("/campaign/{campaign_id}/pilot-readiness")
def gate1_pilot_readiness(campaign_id:int,user:User=Depends(current_user),
                          db:Session=Depends(get_db)):
    """Administrator-only, read-only pilot preflight; never enables writes."""
    _read_enabled()
    officer=_grant(db,user,"administration")
    if not has(officer,"view_intelligence"):
        raise HTTPException(403,"Intelligence view permission required")
    campaign=_campaign(db,officer,campaign_id)
    from .inbox_human_corrections import (
        can_edit_gate1, is_pilot_qa_campaign, PILOT_QA_PROVIDER, _allowlist,
    )
    from .campaigns import _editable
    from .inbox_gate_real_qa_v1867 import is_qa_campaign
    from .models import CampaignEvidence, SocialListeningResult
    synthetic_count=(db.query(CampaignEvidence.id).join(
        SocialListeningResult,
        SocialListeningResult.id==CampaignEvidence.result_id,
    ).filter(
        CampaignEvidence.campaign_id==campaign_id,
        CampaignEvidence.match_method!="WATCHLIST_ACCOUNT",
        SocialListeningResult.provider==PILOT_QA_PROVIDER,
        SocialListeningResult.provider_result_id.like("GATE1-QA-%"),
    ).count())
    # Match Gate 1's ordinary-evidence scope: watchlist-account-only links
    # are intentionally excluded and must not veto a synthetic QA pilot.
    linked_count=(db.query(CampaignEvidence.id).filter(
        CampaignEvidence.campaign_id==campaign_id,
        CampaignEvidence.match_method!="WATCHLIST_ACCOUNT",
    ).count())
    return {
        "campaign_id":str(campaign_id),
        "human_review_read_enabled":True,
        "correction_writes_enabled":_write_enabled(),
        "staging_pilot_mode":os.getenv("BAWASLU_INBOX_GATE1_PILOT_MODE","").strip().lower()=="staging",
        "campaign_allowlisted":campaign.id in _allowlist(),
        "officer_has_human_validation":has(officer,"human_validation"),
        "officer_has_edit_intelligence":has(officer,"edit_intelligence"),
        "officer_can_edit_campaign":_editable(officer,campaign),
        "pilot_campaign_draft_and_named":is_pilot_qa_campaign(campaign) or is_qa_campaign(campaign),
        "qa_pilot_type":"REAL_AUDIT_ONLY" if is_qa_campaign(campaign) else "SYNTHETIC",
        "qa_real_evidence_count":linked_count-synthetic_count if is_qa_campaign(campaign) else 0,
        "linked_source_count":linked_count,
        "pilot_has_ordinary_evidence":linked_count > 0,
        "pilot_empty_reason":(
            "No ordinary evidence linked to this QA campaign; all filters will be empty."
            if linked_count == 0 else None
        ),
        "fixture_seeding_on_shared_db_supported":False,
        "isolated_qa_fixture_required":linked_count == 0,
        "synthetic_source_count":synthetic_count,
        "non_synthetic_link_count":linked_count-synthetic_count,
        "ready_for_write_pilot":bool(can_edit_gate1(officer,campaign)
                                      and ((synthetic_count>0 and linked_count==synthetic_count)
                                           or (is_qa_campaign(campaign) and linked_count>0))),
        "qa_overrides_affect_canonical_ai":False if is_qa_campaign(campaign) else None,
        "writes_triggered":False,
        "source_ids_exposed":False,
        "no_automatic_publication":True,
        "paid_provider_called":False,
    }


@router.get("/campaign/{campaign_id}/queue")
def review_queue(campaign_id:int, page_size:int=40, cursor:int|None=None,
                 category:str="all", review_status:str="all", focus:str="all",
                 user:User=Depends(current_user), db:Session=Depends(get_db)):
    """Full ordinary-evidence Gate 1 queue; read-only, cursor-paginated, scoped."""
    _read_enabled()
    officer=_grant(db,user,"view_intelligence")
    _campaign(db,officer,campaign_id)
    return paginated_review_queue(db,officer,campaign_id,page_size,cursor,category,review_status,focus)
