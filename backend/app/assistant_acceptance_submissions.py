"""Restricted acceptance-evidence metadata submissions and independent review.

Readiness and CSV endpoints remain separate and DO NOT infer signoff from these
events. No legal determination or formal client acceptance is recorded here.
"""
import re
from collections import Counter
from fastapi import APIRouter,Depends,HTTPException,Response
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .access import profile,has
from .models import User,AssistantAcceptanceEvidence,AssistantAcceptanceEvidenceEvent
from .assistant_acceptance_evidence import TRACK_REQUIREMENTS

router=APIRouter(prefix="/api/assistant-evaluation/acceptance-submissions",
                 tags=["assistant-evaluation"])
_REFERENCE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{7,159}$")
_REVIEW_ACTIONS={"EVIDENCE_REVIEWED","REVISION_REQUESTED"}

class EvidenceSubmit(BaseModel):
    track:str
    reference:str=Field(min_length=8,max_length=160)

class EvidenceReview(BaseModel):
    action:str

def _admin(db,user):
    access=profile(db,user)
    if access.get("role")!="National Administrator" or (
        access.get("geographic_scope")!="Nationwide") or not has(access,"administration") or not has(access,"view_intelligence"):
        raise HTTPException(403,"National Administrator access required")
    return access

def _row(db,entry,events=None):
    if events is None:
        events=db.query(AssistantAcceptanceEvidenceEvent).filter(
            AssistantAcceptanceEvidenceEvent.evidence_id==entry.id).order_by(
            AssistantAcceptanceEvidenceEvent.id.asc()).all()
    actions=[e.action for e in events]
    state=("REVIEWED" if actions and actions[-1]=="EVIDENCE_REVIEWED"
           else "REVISION_REQUESTED" if actions and actions[-1]=="REVISION_REQUESTED"
           else "SUBMITTED_UNVERIFIED")
    return {"id":entry.id,"track":entry.track,"reference":entry.reference,
            "status":state,"submitted_by_user_id":entry.submitted_by,
            "submitted_at":entry.submitted_at.isoformat(),
            "history":[{"action":ev.action,"actor_user_id":ev.actor_id,
                        "at":ev.created_at.isoformat()} for ev in events],
            "legal_signoff":False,"client_acceptance":False}

@router.post("")
def submit_evidence(payload:EvidenceSubmit,response:Response,
                    user:User=Depends(current_user),db:Session=Depends(get_db)):
    _admin(db,user)
    reference=payload.reference.strip()
    if payload.track not in TRACK_REQUIREMENTS or not _REFERENCE.fullmatch(reference) or (
        "://" in reference or ".." in reference):
        raise HTTPException(422,"Known track and bounded opaque evidence reference required")
    entry=AssistantAcceptanceEvidence(
        track=payload.track,reference=reference,submitted_by=user.id)
    db.add(entry)
    db.flush()
    db.add(AssistantAcceptanceEvidenceEvent(
        evidence_id=entry.id,actor_id=user.id,action="SUBMITTED"))
    db.commit()
    db.refresh(entry)
    response.headers["Cache-Control"]="private, no-store"
    return _row(db,entry)

@router.post("/{evidence_id}/review")
def review_evidence(evidence_id:int,payload:EvidenceReview,response:Response,
                    user:User=Depends(current_user),db:Session=Depends(get_db)):
    _admin(db,user)
    if payload.action not in _REVIEW_ACTIONS or evidence_id<=0:
        raise HTTPException(422,"Invalid review action or evidence ID")
    # Lock the parent submission for the duration of the review transaction.
    # PostgreSQL serializes concurrent reviewers on this row; after acquiring
    # the lock, the second reviewer sees the committed first decision.
    entry=db.query(AssistantAcceptanceEvidence).filter(
        AssistantAcceptanceEvidence.id==evidence_id).with_for_update().one_or_none()
    if not entry:
        raise HTTPException(404,"Submission not found")
    if entry.submitted_by==user.id:
        raise HTTPException(409,"Independent reviewer required")
    history=db.query(AssistantAcceptanceEvidenceEvent).filter(
        AssistantAcceptanceEvidenceEvent.evidence_id==entry.id).order_by(
        AssistantAcceptanceEvidenceEvent.id.desc()).first()
    if history and history.action in _REVIEW_ACTIONS:
        raise HTTPException(409,"Review already recorded; submit revised evidence as a new entry")
    db.add(AssistantAcceptanceEvidenceEvent(
        evidence_id=entry.id,actor_id=user.id,action=payload.action))
    db.commit()
    response.headers["Cache-Control"]="private, no-store"
    return _row(db,entry)

@router.get("")
def list_evidence(response:Response,user:User=Depends(current_user),
                  db:Session=Depends(get_db)):
    _admin(db,user)
    entries=db.query(AssistantAcceptanceEvidence).order_by(
        AssistantAcceptanceEvidence.id.desc()).limit(101).all()
    truncated=len(entries)>100
    entries=entries[:100]
    grouped={entry.id:[] for entry in entries}
    if entries:
        # One bounded history query replaces a separate DB read per submission.
        events=db.query(AssistantAcceptanceEvidenceEvent).filter(
            AssistantAcceptanceEvidenceEvent.evidence_id.in_(list(grouped))).order_by(
            AssistantAcceptanceEvidenceEvent.evidence_id.asc(),
            AssistantAcceptanceEvidenceEvent.id.asc()).all()
        for event in events:
            grouped[event.evidence_id].append(event)
    data=[_row(db,e,grouped[e.id]) for e in entries]
    counts=dict(Counter(r["status"] for r in data))
    tracks={}
    for track in TRACK_REQUIREMENTS:
        matching=[r for r in data if r["track"]==track]
        track_counts=Counter(r["status"] for r in matching)
        tracks[track]={
            "visible_submissions":len(matching),
            "awaiting_review":track_counts["SUBMITTED_UNVERIFIED"],
            "evidence_reviewed_not_formally_approved":track_counts["REVIEWED"],
            "revision_requested":track_counts["REVISION_REQUESTED"],
            "has_formal_approval":False
        }
    response.headers["Cache-Control"]="private, no-store"
    return {"schema":"BAWASLU_ACCEPTANCE_SUBMISSION_REGISTER_V1596",
            "entries":data,"visible_limit":100,
            "historical_records_may_be_excluded":truncated,
            "counts_scope":"MOST_RECENT_100_SUBMISSIONS_ONLY",
            "status_counts":counts,"track_progress":tracks,
            "external_acceptance_tracks_pending":True,
            "formal_legal_signoff_verified":False,
            "formal_client_acceptance_verified":False,
            "independent_evidence_review_is_not_formal_signoff":True}
