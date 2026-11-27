"""v186.7: Politk Uang Campaign 9 audit-only Human Gate 1 overlay.
Changes only append AuditEvent; no original source, canonical AI, provider data,
insight, training, or Command Centre model is modified.
"""
import json
import os
from datetime import datetime, timezone
from fastapi import HTTPException
from .models import AuditEvent, CampaignEvidence, EvidenceAssessment
from .officer_sentiment import OfficerSentimentCorrection
from .inbox_gate_integrity import GATE1_AUDIT_SUBJECT, audit_payload, source_integrity_digest

QA_ID=9
QA_NAME="Politik Uang"
QA_CONFIRM="POLITIK_UANG_AUDIT_ONLY"
QA_ACTION="GATE1_QA_FIELD_CORRECTED"
QA_ACTIONS=("GATE1_FIELD_CORRECTED","GATE1_FIELD_RESTORED",QA_ACTION)
VALUES={
    "relevance":frozenset(("RELEVANT","HIGHLY_RELEVANT","UNCERTAIN","IRRELEVANT")),
    "sentiment":frozenset(("POSITIVE","NEGATIVE","NEUTRAL")),
}

def is_qa_campaign(campaign):
    return bool(campaign and campaign.id==QA_ID and campaign.name==QA_NAME and campaign.status=="DRAFT")

def qa_write_opt_in(campaign):
    return bool(is_qa_campaign(campaign)
        and os.getenv("BAWASLU_INBOX_GATE1_REAL_QA_CAMPAIGN_ID")=="9"
        and os.getenv("BAWASLU_INBOX_GATE1_REAL_QA_CONFIRM")==QA_CONFIRM)

def isolated_source(db,campaign,source):
    if not is_qa_campaign(campaign) or source is None or source.promoted_intelligence_id is not None:
        return False
    return db.query(CampaignEvidence.id).filter(
        CampaignEvidence.result_id==source.id,CampaignEvidence.campaign_id!=QA_ID).first() is None

def events(db,campaign_id,result_id):
    if campaign_id!=QA_ID:return []
    return db.query(AuditEvent).filter_by(
        subject_type=GATE1_AUDIT_SUBJECT,subject_id=f"{QA_ID}:{result_id}",
        action=QA_ACTION).order_by(AuditEvent.id.desc()).limit(200).all()

def projection(db,campaign_id,result_id,assessment,sentiment,source):
    result={
        "effective_relevance":assessment.relevance_label if assessment else "UNASSESSED",
        "relevance_basis":"SAVED_ASSESSMENT" if assessment else "UNASSESSED",
        "effective_sentiment":sentiment.sentiment if sentiment else (assessment.sentiment if assessment else "UNKNOWN"),
        "sentiment_basis":"OFFICER_CORRECTION" if sentiment else "SAVED_ASSESSMENT",
        "relevance_revision":assessment.assessment_version if assessment else 0,
        "sentiment_revision":sentiment.id if sentiment else 0,
        "qa_relevance_event":0,"qa_sentiment_event":0,"qa_stale":False,
        "qa_audit_only":campaign_id==QA_ID,
    }
    if campaign_id!=QA_ID:return result
    seen=set();digest=source_integrity_digest(source)
    for e in events(db,campaign_id,result_id):
        p=audit_payload(e);field=p.get("field_name")
        if field not in VALUES or field in seen:continue
        seen.add(field)
        if (p.get("source_integrity_digest")!=digest
            or p.get("assessment_id_before_correction")!=(assessment.id if assessment else None)
            or p.get("new_effective_value") not in VALUES[field]):
            result["qa_stale"]=True
            continue
        result[f"effective_{field}"]=p["new_effective_value"]
        result[f"{field}_basis"]="QA_OFFICER_OVERRIDE"
        result[f"{field}_revision"]=e.id
        result[f"qa_{field}_event"]=e.id
    return result

def reviewed_state(db,campaign_id,result_id,assessment,sentiment,source,state):
    if campaign_id!=QA_ID:return state
    from .inbox_human_corrections import _latest_decision
    e=_latest_decision(db,campaign_id,result_id)
    if e is None:return state
    p=audit_payload(e);o=projection(db,campaign_id,result_id,assessment,sentiment,source)
    if (o["qa_stale"] or
        p.get("qa_relevance_event")!=o["qa_relevance_event"] or
        p.get("qa_sentiment_event")!=o["qa_sentiment_event"]):
        return {**state,"information_review_status":"REVALIDATION_REQUIRED",
                "information_review_stale":True}
    return state

def save(db,user,officer,campaign_id,source,assessment,sentiment,field,value,
         expected_revision,expected_assessment_id,expected_source_digest,reason,restored_from=None):
    if campaign_id!=QA_ID or field not in VALUES or value not in VALUES[field]:
        raise HTTPException(422,"Invalid QA correction")
    if source_integrity_digest(source)!=expected_source_digest:
        raise HTTPException(409,"Source changed; refresh")
    if assessment is None or assessment.id!=expected_assessment_id:
        raise HTTPException(409,"Assessment changed; refresh")
    before=projection(db,campaign_id,source.id,assessment,sentiment,source)
    if before["qa_stale"] or before[f"{field}_revision"]!=expected_revision:
        raise HTTPException(409,"QA correction revision changed; refresh")
    old=str(before[f"effective_{field}"] or "").upper()
    if old==value:raise HTTPException(422,"No correction: value already effective")
    e=AuditEvent(
        subject_type=GATE1_AUDIT_SUBJECT,subject_id=f"{QA_ID}:{source.id}",
        action=QA_ACTION,actor_id=str(user.id),actor_name=str(officer.get("name") or "")[:255],
        changes_json=json.dumps({
            "campaign_id":QA_ID,"result_id":source.id,"field_name":field,
            "old_effective_value":old,"new_effective_value":value,
            "previous_revision":expected_revision,"reason":reason,"reviewer_id":str(user.id),
            "source_integrity_digest":expected_source_digest,
            "assessment_id_before_correction":assessment.id,
            "qa_audit_only":True,"original_source_preserved":True,
            "canonical_assessment_preserved":True,"official_insight_published":False,
            "model_training_triggered":False,"restored_from":restored_from,
        },sort_keys=True,ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat())
    db.add(e);db.commit()
    return {"saved":True,"field":field,"effective_value":value,"revision":e.id,
            "correction_id":e.id,"review_status":"FIELD_CORRECTED",
            "qa_audit_only":True,"revalidation_required":True,
            "automatic_publication":False,"paid_provider_called":False}

def history(db,campaign_id,result_id):
    relevance=[];sentiment=[]
    for e in events(db,campaign_id,result_id):
        p=audit_payload(e)
        row={"revision":e.id,"value":p.get("new_effective_value"),
             "model_version":"QA_AUDIT_ONLY","reviewer_id":e.actor_id,
             "reason":p.get("reason"),"created_at":e.occurred_at}
        (relevance if p.get("field_name")=="relevance" else sentiment).append(row)
    return relevance,sentiment

def restore_value(db,campaign_id,result_id,assessment,field,target_revision):
    if field not in VALUES or campaign_id!=QA_ID:return None
    for e in events(db,campaign_id,result_id):
        if e.id==target_revision and audit_payload(e).get("field_name")==field:
            return audit_payload(e).get("new_effective_value")
    if field=="relevance":
        e=db.query(EvidenceAssessment).filter_by(
            campaign_id=campaign_id,result_id=result_id,
            assessment_version=target_revision).first()
        return e.relevance_label if e else None
    if target_revision==0:return assessment.sentiment if assessment else None
    s=db.query(OfficerSentimentCorrection).filter_by(
        campaign_id=campaign_id,result_id=result_id,id=target_revision).first()
    return s.sentiment if s else None
