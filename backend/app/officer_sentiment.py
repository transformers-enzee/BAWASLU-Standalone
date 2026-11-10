"""Human sentiment overrides: one campaign/source truth shared by SL, Inbox, AI.

Corrections are appended, not destructive edits to AI assessments. Officer
authority and campaign/source scope are checked for every mutation.
"""
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import DateTime,ForeignKey,Integer,String,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column,Session
from .db import Base,get_db
from .auth import current_user
from .access import profile,has
from .models import User,CampaignEvidence,MonitoringCampaign,SocialListeningResult

router=APIRouter(prefix="/api/officer-sentiment",tags=["officer-sentiment"])
LABELS={"POSITIVE","NEUTRAL","NEGATIVE"}
class OfficerSentimentCorrection(Base):
    __tablename__="officer_sentiment_corrections"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    campaign_id:Mapped[int]=mapped_column(Integer,ForeignKey("monitoring_campaigns.id"),index=True,nullable=False)
    result_id:Mapped[int]=mapped_column(Integer,ForeignKey("social_listening_results.id"),index=True,nullable=False)
    sentiment:Mapped[str]=mapped_column(String(16),nullable=False)
    rationale:Mapped[str]=mapped_column(Text,nullable=False)
    actor_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"),nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=lambda:datetime.now(timezone.utc),nullable=False)

class CorrectionBody(BaseModel):
    campaign_id:int=Field(gt=0)
    result_id:int=Field(gt=0)
    sentiment:str
    rationale:str=Field(default="",max_length=1000)

def _verify(db,p,campaign_id,result_id,write=False):
    from .access import allowed
    from .socialcrawl import _result_in_scope
    if not has(p,"edit_intelligence" if write else "view_intelligence"):
        raise HTTPException(403,"Officer permission required")
    campaign=db.get(MonitoringCampaign,campaign_id)
    post=db.get(SocialListeningResult,result_id)
    link=db.query(CampaignEvidence.id).filter_by(campaign_id=campaign_id,result_id=result_id).first()
    if not campaign or not allowed(p,campaign) or not post or not link or not _result_in_scope(db,p,post):
        raise HTTPException(403,"Evidence is not accessible within this campaign")
    return campaign,post

def latest_corrections(db,keys):
    """One bounded query for each returned page; no N+1 per-row correction reads."""
    pairs={(int(c),int(r)) for c,r in keys if str(c).isdigit() and str(r).isdigit()}
    if not pairs:return {}
    from sqlalchemy import tuple_
    results=db.query(OfficerSentimentCorrection).filter(
        tuple_(OfficerSentimentCorrection.campaign_id,OfficerSentimentCorrection.result_id).in_(list(pairs))
    ).order_by(OfficerSentimentCorrection.id.desc()).all()
    latest={}
    for row in results:
        key=(row.campaign_id,row.result_id)
        if key not in latest:latest[key]=row
    return latest

def correction_view(row):
    if not row:return None
    return {"sentiment":row.sentiment,"rationale":row.rationale,"actor_id":row.actor_id,
            "corrected_at":row.created_at.isoformat() if row.created_at else None,
            "correction_id":row.id,"origin":"OFFICER_CORRECTION"}

def effective_sentiment(db,campaign_id,result_id,ai_label="UNCLASSIFIED"):
    row=latest_corrections(db,[(campaign_id,result_id)]).get((int(campaign_id),int(result_id)))
    return row.sentiment if row else str(ai_label or "UNCLASSIFIED").upper()

@router.post("/correct")
def correct_sentiment(body:CorrectionBody,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    _,post=_verify(db,p,body.campaign_id,body.result_id,True)
    label=body.sentiment.upper().strip()
    if label not in LABELS:
        raise HTTPException(422,"Sentiment must be POSITIVE, NEUTRAL or NEGATIVE")
    # Optional compatibility field: no explanation is required for a manual
    # correction. The actor, source, previous value and timestamp are audited.
    note=(body.rationale or "").strip()
    previous=latest_corrections(db,[(body.campaign_id,body.result_id)]).get((body.campaign_id,body.result_id))
    if previous and previous.sentiment==label:
        return {"correction":correction_view(previous),"unchanged":True,"paid_provider_called":False}
    row=OfficerSentimentCorrection(campaign_id=body.campaign_id,result_id=body.result_id,
            sentiment=label,rationale=note,actor_id=user.id)
    db.add(row);db.flush()
    from .models import AuditEvent
    import json
    db.add(AuditEvent(subject_type="SocialListeningResult",
        subject_id=str(body.result_id),action="OFFICER_SENTIMENT_CORRECTED",
        actor_id=str(user.id),actor_name=p.get("name",""),
        changes_json=json.dumps({"campaign_id":body.campaign_id,"new":label,
            "old_officer_value":previous.sentiment if previous else None,
            "rationale":note},ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat()))
    db.commit()
    return {"correction":correction_view(row),"unchanged":False,"paid_provider_called":False}

@router.get("/history/{campaign_id}/{result_id}")
def correction_history(campaign_id:int,result_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    _verify(db,p,campaign_id,result_id)
    rows=db.query(OfficerSentimentCorrection).filter_by(
        campaign_id=campaign_id,result_id=result_id).order_by(
        OfficerSentimentCorrection.id.desc()).limit(30).all()
    return {"corrections":[correction_view(row) for row in rows]}
