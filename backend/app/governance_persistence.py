"""BAWASLU v184.5 governance review persistence.

Explicit opt-in until the additive schema is applied and validated on staging.
No provider calls, no source mutation, no automatic Command Centre publication.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .access import allowed, has, profile
from .auth import current_user
from .db import get_db
from .models import (User, MonitoringCampaign, CampaignEvidence,
                     SocialListeningResult, EvidenceAssessment,
                     GovernanceFieldCorrection, GovernanceInsight,
                     EvidenceReview)
from .intelligence_contract import OVERRIDABLE_FIELDS
from .human_governance_gates import information_gate, insight_publication_gate
from .governance_projection import (effective_assessment, source_snapshot_fingerprint,
                                     MAX_CORRECTIONS_PER_SOURCE)
from .governance_integration import active as governance_reads_active

router = APIRouter(prefix="/api/governance", tags=["governance"])
MAX_REFERENCES = 100

def _enabled():
    if os.getenv("BAWASLU_GOVERNANCE_WRITES_ENABLED", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(503, "Governance persistence is disabled until schema verification")

def _grant(db, user, permission):
    p = profile(db, user)
    if not has(p, permission):
        raise HTTPException(403, "Officer authorization required")
    return p

def _campaign(db, p, campaign_id):
    campaign = db.get(MonitoringCampaign, campaign_id)
    if not campaign or not allowed(p, campaign):
        raise HTTPException(404, "Campaign unavailable")
    return campaign

def _source(db, p, campaign_id, result_id):
    if not db.query(CampaignEvidence.id).filter_by(campaign_id=campaign_id, result_id=result_id).first():
        raise HTTPException(404, "Source not linked to authorized campaign")
    result = db.get(SocialListeningResult, result_id)
    if not result:
        raise HTTPException(404, "Source unavailable")
    from .socialcrawl import _result_in_scope
    if not _result_in_scope(db, p, result):
        raise HTTPException(404, "Source unavailable")
    return result

def _snapshot(db, p, campaign_id, ids):
    if not ids or len(ids) > MAX_REFERENCES or len(ids) != len(set(ids)):
        raise HTTPException(422, "Use 1-100 distinct source references")
    pieces = []
    for result_id in sorted(ids):
        post = _source(db, p, campaign_id, result_id)
        assessment = db.query(EvidenceAssessment).filter_by(
            campaign_id=campaign_id, result_id=result_id
        ).order_by(EvidenceAssessment.assessment_version.desc(),
                   EvidenceAssessment.id.desc()).first()
        corrections = _correction_rows(db, campaign_id, result_id)
        # Existing officer actions are still authoritative in the legacy Inbox.
        # A subsequent legacy override/review must invalidate this snapshot.
        from .officer_sentiment import OfficerSentimentCorrection
        legacy_sentiment = (db.query(OfficerSentimentCorrection).filter_by(
            campaign_id=campaign_id, result_id=result_id
        ).order_by(OfficerSentimentCorrection.id.desc()).first())
        evidence_review = None
        if assessment is not None:
            evidence_review=(db.query(EvidenceReview).filter_by(
                assessment_id=assessment.id
            ).order_by(EvidenceReview.id.desc()).first())
        pieces.append([result_id, source_snapshot_fingerprint(
            post, assessment, corrections,
            {"officer_sentiment":legacy_sentiment, "evidence_review":evidence_review}
        )])
    return hashlib.sha256(json.dumps(pieces, sort_keys=True).encode("utf-8")).hexdigest()

def _correction_rows(db, campaign_id, result_id):
    rows = (db.query(GovernanceFieldCorrection)
            .filter_by(campaign_id=campaign_id, result_id=result_id)
            .order_by(GovernanceFieldCorrection.id.asc())
            .limit(MAX_CORRECTIONS_PER_SOURCE + 1).all())
    if len(rows) > MAX_CORRECTIONS_PER_SOURCE:
        raise HTTPException(409, "Correction history exceeds bounded review limit")
    return rows


def _approved_row_gate(row, ids, current):
    return insight_publication_gate({
        "state": row.state, "approver_id": str(row.approver_id or ""),
        "approved_revision": str(row.revision) if row.revision else "",
        "finding_id": str(row.id), "evidence_refs": [str(x) for x in ids],
        "analysis_scope": row.analysis_scope, "source_revision_current": current,
        "claim_status": row.claim_status, "evidence_verified": row.evidence_verified,
        "contains_high_impact_claims": row.contains_high_impact_claims,
        "high_impact_reviewed": row.high_impact_reviewed,
    })


class CorrectionIn(BaseModel):
    campaign_id: int = Field(gt=0)
    result_id: int = Field(gt=0)
    field: str = Field(min_length=1, max_length=80)
    human_value: str = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=10, max_length=1500)
    expected_revision: int = Field(ge=0)

class InsightIn(BaseModel):
    campaign_id: int = Field(gt=0)
    title: str = Field(min_length=8, max_length=255)
    evidence_result_ids: list[int] = Field(min_length=1, max_length=100)
    analysis_scope: str = Field(min_length=6, max_length=180)
    claim_status: str = Field(default="preliminary")
    evidence_verified: bool = False
    contains_high_impact_claims: bool = False
    high_impact_reviewed: bool = False

class DecisionIn(BaseModel):
    expected_revision: int = Field(gt=0)
    decision: str
    rationale: str = Field(min_length=10, max_length=1500)

@router.post("/information/overrides")
def submit_override(body: CorrectionIn, user: User=Depends(current_user), db: Session=Depends(get_db)):
    _enabled()
    p = _grant(db, user, "human_validation")
    _campaign(db, p, body.campaign_id)
    post = _source(db, p, body.campaign_id, body.result_id)
    # v184.7: only validated fields can affect effective-value reads.
    # Other classifications stay in the existing specialized officer-review flows.
    if body.field not in ("sentiment","relevance"):
        raise HTTPException(422, "Use the supported sentiment or relevance field") 
    if body.field=="sentiment" and body.human_value.strip().upper() not in ("POSITIVE","NEUTRAL","NEGATIVE"):
        raise HTTPException(422, "Invalid sentiment value")
    if body.field=="relevance" and body.human_value.strip().upper() not in ("RELEVANT","HIGHLY_RELEVANT","IRRELEVANT","UNCERTAIN"):
        raise HTTPException(422, "Invalid election-relevance value")
    if not post.text_content and not post.canonical_url:
        raise HTTPException(422, "Missing original content and URL")
    # Serialize competing corrections on the existing source row; the original stays unchanged.
    db.query(SocialListeningResult).filter_by(id=post.id).with_for_update().first()
    latest = (db.query(GovernanceFieldCorrection)
              .filter_by(campaign_id=body.campaign_id, result_id=body.result_id,
                         field=body.field)
              .order_by(GovernanceFieldCorrection.revision.desc()).first())
    previous = latest.revision if latest else 0
    if previous != body.expected_revision:
        raise HTTPException(409, "Review revision changed; refresh before correcting")
    row = GovernanceFieldCorrection(
        campaign_id=body.campaign_id, result_id=body.result_id, field=body.field,
        human_value=body.human_value.strip().upper(), reason=body.reason.strip(),
        reviewer_id=user.id, revision=previous + 1,
        status="approved", created_at=datetime.utcnow())
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Concurrent correction; refresh")
    return {"correction_id":row.id, "revision":row.revision, "status":"approved",
            "source_preserved":True, "reassessment_required":True}

@router.get("/information/overrides/{campaign_id}/{result_id}")
def list_overrides(campaign_id:int, result_id:int, user:User=Depends(current_user),
                   db:Session=Depends(get_db)):
    _enabled()
    p=_grant(db,user,"view_intelligence")
    _campaign(db,p,campaign_id)
    _source(db,p,campaign_id,result_id)
    rows=_correction_rows(db,campaign_id,result_id)
    return {"records":[{"field":r.field,"value":r.human_value,"reason":r.reason,
                        "reviewer_id":r.reviewer_id,"revision":r.revision,
                        "created_at":r.created_at.isoformat()} for r in rows],
            "raw_source_unchanged":True}

@router.post("/insights")
def propose_insight(body: InsightIn, user:User=Depends(current_user), db:Session=Depends(get_db)):
    _enabled()
    p=_grant(db,user,"human_validation")
    _campaign(db,p,body.campaign_id)
    # Self-asserted evidence verification is never a trustworthy approval signal.
    if body.claim_status != "preliminary" or body.evidence_verified or body.high_impact_reviewed:
        raise HTTPException(422,"Verified claims require an independent evidence workflow")
    if any(isinstance(x,bool) or x <= 0 for x in body.evidence_result_ids):
        raise HTTPException(422,"Evidence references must be positive source IDs")
    digest=_snapshot(db,p,body.campaign_id,body.evidence_result_ids)
    row=GovernanceInsight(
        campaign_id=body.campaign_id,title=body.title.strip(),
        evidence_ids_json=json.dumps(body.evidence_result_ids),
        analysis_scope=body.analysis_scope.strip(),
        claim_status=body.claim_status,evidence_verified=body.evidence_verified,
        contains_high_impact_claims=body.contains_high_impact_claims,
        high_impact_reviewed=body.high_impact_reviewed,
        source_digest=digest, state="pending_approval", revision=1,
        proposer_id=user.id, created_at=datetime.utcnow())
    db.add(row);db.commit();db.refresh(row)
    return {"insight_id":row.id,"status":"pending_approval","published":False,
            "revision":row.revision}

@router.post("/insights/{insight_id}/decision")
def decide_insight(insight_id:int,body:DecisionIn,user:User=Depends(current_user),
                   db:Session=Depends(get_db)):
    _enabled()
    p=_grant(db,user,"verify_evidence")
    row=db.query(GovernanceInsight).filter_by(id=insight_id).with_for_update().first()
    if not row:raise HTTPException(404,"Insight unavailable")
    _campaign(db,p,row.campaign_id)
    if row.revision!=body.expected_revision or row.state!="pending_approval":
        raise HTTPException(409,"Insight changed or already decided")
    if body.decision not in ("approve","reject"):
        raise HTTPException(422,"Invalid decision")
    # Human Gate 2 must be an independent decision, even for routine findings.
    # High-impact findings also require the specialist validation guard below.
    if row.proposer_id==user.id and body.decision=="approve":
        raise HTTPException(403,"An independent officer must approve the insight")
    ids=json.loads(row.evidence_ids_json)
    fresh=_snapshot(db,p,row.campaign_id,ids)
    candidate={"state":"approved" if body.decision=="approve" else "rejected",
        "approver_id":str(user.id),"approved_revision":str(row.revision),
        "finding_id":str(row.id),"evidence_refs":[str(x) for x in ids],
        "analysis_scope":row.analysis_scope,
        "source_revision_current":fresh==row.source_digest,
        "claim_status":row.claim_status,"evidence_verified":row.evidence_verified,
        "contains_high_impact_claims":row.contains_high_impact_claims,
        "high_impact_reviewed":bool(row.contains_high_impact_claims and
                                    row.proposer_id!=user.id and body.decision=="approve")}
    verdict=insight_publication_gate(candidate)
    if body.decision=="approve" and not verdict["publish_allowed"]:
        raise HTTPException(409,{"review_blockers":verdict["review_blockers"]})
    row.state="approved" if body.decision=="approve" else "rejected"
    row.high_impact_reviewed=bool(row.contains_high_impact_claims and
                                  row.proposer_id!=user.id and body.decision=="approve")
    row.approver_id=user.id
    row.review_rationale=body.rationale.strip()
    row.reviewed_at=datetime.utcnow()
    row.revision+=1
    db.commit()
    return {"insight_id":row.id,"state":row.state,
            "publication_eligible":body.decision=="approve",
            "legacy_command_centre_unchanged":True}

@router.get("/insights")
def list_insights(campaign_id:int,user:User=Depends(current_user),
                  db:Session=Depends(get_db)):
    _enabled()
    p=_grant(db,user,"view_intelligence")
    _campaign(db,p,campaign_id)
    rows=(db.query(GovernanceInsight).filter_by(campaign_id=campaign_id)
          .order_by(GovernanceInsight.id.desc()).limit(100).all())
    items=[]
    for row in rows:
        ids=json.loads(row.evidence_ids_json)
        current=_snapshot(db,p,campaign_id,ids)==row.source_digest
        result=_approved_row_gate(row,ids,current)
        items.append({"id":row.id,"title":row.title,"state":row.state,
                      "revision":row.revision,"sources_current":current,
                      "publication_eligible":result["publish_allowed"],
                      "review_blockers":result["review_blockers"]})
    return {"items":items,"legacy_command_centre_unchanged":True}


@router.get("/information/effective/{campaign_id}/{result_id}")
def effective_information(campaign_id:int,result_id:int,user:User=Depends(current_user),
                          db:Session=Depends(get_db)):
    """Officer-corrected field preview; legacy Inbox reads are not silently altered."""
    _enabled()
    p=_grant(db,user,"view_intelligence")
    _campaign(db,p,campaign_id)
    _source(db,p,campaign_id,result_id)
    assessment=(db.query(EvidenceAssessment).filter_by(
        campaign_id=campaign_id,result_id=result_id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).first())
    corrections=_correction_rows(db,campaign_id,result_id)
    return {"campaign_id":campaign_id,"result_id":result_id,
            **effective_assessment(assessment,corrections),
            "legacy_inbox_unchanged":True}


@router.get("/command-centre/approved")
def approved_command_centre(campaign_id:int,user:User=Depends(current_user),
                            db:Session=Depends(get_db)):
    """Read-only, dynamically refreshed approved-only insight projection.

    This endpoint does not overwrite the existing Command Centre. Any changed
    source, AI assessment or officer correction removes an insight from the feed.
    """
    _enabled()
    p=_grant(db,user,"view_intelligence")
    _campaign(db,p,campaign_id)
    rows=(db.query(GovernanceInsight).filter_by(
        campaign_id=campaign_id,state="approved")
        .order_by(GovernanceInsight.id.desc()).limit(30).all())
    items=[]
    stale=0
    for row in rows:
        try:
            ids=json.loads(row.evidence_ids_json)
            current=_snapshot(db,p,campaign_id,ids)==row.source_digest
            result=_approved_row_gate(row,ids,current)
        except (ValueError,TypeError,HTTPException):
            stale+=1
            continue
        if not result["publish_allowed"]:
            stale+=1
            continue
        items.append({"id":row.id,"campaign_id":campaign_id,
                      "title":row.title,"claim_status":row.claim_status,
                      "review_status":"OFFICER_APPROVED",
                      "evidence_result_ids":ids,"analysis_scope":row.analysis_scope,
                      "approver_id":row.approver_id,
                      "reviewed_at":row.reviewed_at.isoformat() if row.reviewed_at else None,
                      "published_by_legacy_dashboard":False})
    return {"insights":items,"stale_or_blocked_count":stale,
            "approved_only":True,"legacy_command_centre_unchanged":True}


@router.get("/review-queue")
def governance_review_queue(campaign_id:int,limit:int=20,
                            user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Concise read-only officer work queue; zero AI calls or source mutations."""
    if not governance_reads_active():
        raise HTTPException(503,"Governance review queue is not enabled")
    p=_grant(db,user,"view_intelligence")
    _campaign(db,p,campaign_id)
    if not 1<=limit<=50:
        raise HTTPException(422,"Limit must be between 1 and 50")
    rows=(db.query(GovernanceInsight).filter_by(campaign_id=campaign_id)
          .order_by(GovernanceInsight.id.desc()).limit(limit).all())
    cases=[]
    for row in rows:
        try:
            ids=json.loads(row.evidence_ids_json)
            if (not isinstance(ids,list) or not ids
                or any(type(i) is not int or i<=0 for i in ids)):
                raise ValueError("Invalid evidence references")
            source_current=_snapshot(db,p,campaign_id,ids)==row.source_digest
            verdict=_approved_row_gate(row,ids,source_current)
            blockers=verdict["review_blockers"]
        except (ValueError,TypeError,HTTPException):
            source_current=False
            blockers=["EVIDENCE_UNAVAILABLE_OR_OUT_OF_SCOPE"]
        action=("REVIEW_FOR_APPROVAL" if row.state=="pending_approval" and source_current
                else "REASSESS_SOURCE" if not source_current
                else "NO_ACTION")
        cases.append({
            "id":row.id,"title":row.title,"state":row.state,
            "revision":row.revision,"source_current":source_current,
            "review_blockers":blockers,"next_action":action,
            "can_approve":bool(action=="REVIEW_FOR_APPROVAL"
                and has(p,"verify_evidence") and row.proposer_id!=user.id),
            "independent_reviewer_required":True,
        })
    return {
        "campaign_id":campaign_id,"cases":cases,
        "awaiting_review":sum(1 for item in cases if item["next_action"]=="REVIEW_FOR_APPROVAL"),
        "needs_reassessment":sum(1 for item in cases if item["next_action"]=="REASSESS_SOURCE"),
        "read_only":True,"paid_provider_called":False,
    }


@router.get("/readiness")
def governance_readiness(user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Administrators can inspect deployment prerequisites without enabling writes."""
    _grant(db,user,"administration")
    bind=db.get_bind()
    inspector=inspect(bind)
    expected=("governance_field_corrections","governance_insights")
    present={name:inspector.has_table(name) for name in expected}
    access_checked=False
    protected=False
    if bind.dialect.name=="postgresql" and all(present.values()):
        records=db.execute(text(
            "SELECT relname, relrowsecurity,"
            " has_table_privilege('anon',oid,'SELECT') AS anon_read,"
            " has_table_privilege('authenticated',oid,'SELECT') AS auth_read"
            " FROM pg_class WHERE relname IN"
            " ('governance_field_corrections','governance_insights')"
        )).mappings().all()
        access_checked=len(records)==len(expected)
        protected=access_checked and all(
            row["relrowsecurity"] and not row["anon_read"] and not row["auth_read"]
            for row in records)
    writes_enabled=os.getenv("BAWASLU_GOVERNANCE_WRITES_ENABLED","").lower() in ("1","true","yes")
    reads_enabled=governance_reads_active()
    return {
        "schema_tables_present":present,
        "table_access_verified":access_checked,
        "rls_and_privileges_protected":protected,
        "governance_reads_enabled":reads_enabled,
        "governance_writes_enabled":writes_enabled,
        "ready_for_controlled_staging_qa":all(present.values()) and protected,
        "manual_qa_not_started":True,
        "production_promotion_authorized":False,
        "paid_provider_called":False,
    }
