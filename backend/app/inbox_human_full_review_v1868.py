"""v186.8 Human Gate 1 full-field information QA: append-only, campaign 9 only.

Original social-listening provider rows, canonical AI assessments and operational
projections are NEVER mutated. Multi-field patches and manual missing-source
proposals live exclusively in the existing AuditEvent ledger.
"""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .access import has
from .auth import current_user
from .db import get_db
from .governance_persistence import _campaign, _grant, _source
from .inbox_gate_integrity import GATE1_AUDIT_SUBJECT, audit_payload, source_integrity_digest
from .inbox_gate_real_qa_v1867 import QA_ID, is_qa_campaign
from .models import AuditEvent, EvidenceAssessment, SocialListeningResult, User

router = APIRouter(prefix="/api/inbox/human-review", tags=["inbox-human-review"])

FULL_ACTION = "GATE1_QA_FULL_RECORD_ENRICHED"
SECOND_ACTION = "GATE1_QA_SECOND_REVIEW"
MANUAL_ACTION = "GATE1_QA_MANUAL_EVIDENCE"
FIELD_GROUPS = {
    "source": (
        "platform", "content_type", "author_name", "observed_handle", "published_at",
        "canonical_url", "text_content", "language", "transcript", "translation",
        "country", "province", "city", "location_basis", "incident_date",
        "engagement_likes", "engagement_comments", "engagement_shares", "engagement_views",
    ),
    "assessment": (
        "candidate_names", "political_parties", "organizations", "topic_labels",
        "public_concerns", "narrative", "potential_issue_categories",
        "relevance_explanation", "sentiment_explanation", "geographic_context",
    ),
    "quality": (
        "evidence_quality", "missing_data", "verification_gaps", "duplicate_reference",
        "officer_notes", "provider_fetch_status",
    ),
}
FIELDS = frozenset(v for names in FIELD_GROUPS.values() for v in names)
SENSITIVE = frozenset((
    "author_name", "observed_handle", "canonical_url", "text_content", "transcript",
    "translation", "candidate_names", "political_parties",
    "organizations", "potential_issue_categories", "country", "province", "city",
    "incident_date", "geographic_context",
))
LONG_FIELDS = frozenset((
    "text_content", "transcript", "translation", "narrative", "officer_notes",
    "verification_gaps", "missing_data", "relevance_explanation", "sentiment_explanation",
))
NUMBERS = frozenset(("engagement_likes","engagement_comments","engagement_shares","engagement_views"))
DATES = frozenset(("published_at","incident_date"))
URL_FIELDS = frozenset(("canonical_url",))
QUALITY_VALUES = frozenset(("COMPLETE","PARTIAL","MISSING","CONFLICTING","UNVERIFIABLE","DUPLICATE"))
PROVIDER_VALUES = frozenset(("AVAILABLE","PARTIAL","API_FAILED","DELETED","ACCESS_RESTRICTED","NOT_RETURNED"))
VERIFICATIONS = frozenset(("UNVERIFIED","OFFICER_SUPPLIED","SOURCE_CONFIRMED"))
REASONS = frozenset(("CORRECTED","SUPPLEMENTED","MISSING_PROVIDER","UNAVAILABLE"))
MAX_BATCH = 15
MAX_AUDIT_EVENTS = 100


class FieldPatch(BaseModel):
    field: str
    value: str = Field(max_length=8000)
    mode: str = "CORRECTED"
    verification: str = "UNVERIFIED"
    evidence_url: str = ""
    field_reason: str = Field(min_length=10, max_length=600)


class FullReviewBatch(BaseModel):
    fields: list[FieldPatch] = Field(min_length=1, max_length=MAX_BATCH)
    expected_revision: int = Field(ge=0)
    expected_assessment_id: int = Field(gt=0)
    expected_source_digest: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=10, max_length=1500)


class SecondReviewIn(BaseModel):
    expected_revision: int = Field(gt=0)
    expected_source_digest: str = Field(min_length=64, max_length=64)
    expected_assessment_id: int = Field(gt=0)
    status: str
    reason: str = Field(min_length=10, max_length=1500)


class ManualEvidenceIn(BaseModel):
    platform: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=255)
    text_content: str = Field(min_length=10, max_length=5000)
    source_url: str = Field(default="", max_length=1000)
    author_name: str = Field(default="", max_length=255)
    observed_at: str = Field(default="", max_length=80)
    reason: str = Field(min_length=10, max_length=1500)
    evidence_url: str = Field(default="", max_length=1000)


def _safe_url(value, required=False):
    value = (value or "").strip()
    if not value:
        if required:
            raise HTTPException(422, "Source reference URL required")
        return ""
    if len(value) > 1200 or any(ord(c) < 32 for c in value):
        raise HTTPException(422, "Invalid reference URL")
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, "Only public HTTP(S) source references are accepted")
    if parsed.hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise HTTPException(422, "Local reference URL is not permitted")
    return value


def _value(field, raw):
    v = raw.strip()
    if len(v) > (8000 if field in LONG_FIELDS else 1000):
        raise HTTPException(422, f"Value too long for {field}")
    if any(c == "\x00" for c in v):
        raise HTTPException(422, "Invalid control character")
    if field in NUMBERS:
        if not re.fullmatch(r"[0-9]{1,14}", v):
            raise HTTPException(422, "Engagement must be a nonnegative whole number")
        v = str(int(v))
    elif field in URL_FIELDS:
        v = _safe_url(v, required=True)
    elif field in DATES and v:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9:.-]{5,24}(Z|[+-][0-9:]{5})?)?", v):
            raise HTTPException(422, "Date/time must use ISO-like format")
    elif field == "evidence_quality" and v not in QUALITY_VALUES:
        raise HTTPException(422, "Unsupported evidence quality")
    elif field == "provider_fetch_status" and v not in PROVIDER_VALUES:
        raise HTTPException(422, "Unsupported provider fetch status")
    elif not v:
        raise HTTPException(422, "Use UNAVAILABLE mode to mark missing information")
    return v


def _baseline(field, source, assessment):
    if field in ("platform","content_type","author_name","observed_handle",
                 "published_at","canonical_url","text_content","language"):
        return str(getattr(source,field,"") or "")
    if field in ("relevance_explanation","sentiment_explanation"):
        name = "explanation" if field == "relevance_explanation" else field
        return str(getattr(assessment,name,"") or "") if assessment else ""
    if field in NUMBERS:
        try:
            data=json.loads(source.engagement_json or "{}")
            return str(data.get(field.removeprefix("engagement_"),"") or "") if isinstance(data,dict) else ""
        except (ValueError,TypeError):
            return ""
    nested_ai={
        "candidate_names":"candidate_signals_json",
        "political_parties":"player_summaries_json",
        "organizations":"player_summaries_json",
        "topic_labels":"topic_labels_json",
        "public_concerns":"public_concern_signals_json",
        "potential_issue_categories":"potential_issue_signals_json",
        "geographic_context":"geographic_signals_json",
    }
    if field in nested_ai and assessment is not None:
        return str(getattr(assessment,nested_ai[field],"") or "")
    if field in ("country","province","city","location_basis"):
        try:
            geo=json.loads(source.geography_json or "{}")
            return str(geo.get(field,"") or "") if isinstance(geo,dict) else ""
        except (ValueError,TypeError):
            return ""
    return ""


def _recent(db,campaign_id,result_id):
    return (db.query(AuditEvent)
            .filter_by(subject_type=GATE1_AUDIT_SUBJECT,subject_id=f"{campaign_id}:{result_id}",
                       action=FULL_ACTION)
            .order_by(AuditEvent.id.desc()).limit(MAX_AUDIT_EVENTS).all())


def second_review_state(db,campaign_id,result_id,revision):
    if not revision:
        return {"status":"NOT_REQUIRED","reviewer_id":None,"reason":None}
    latest=(db.query(AuditEvent)
            .filter_by(subject_type=GATE1_AUDIT_SUBJECT,
                       subject_id=f"{campaign_id}:{result_id}",action=SECOND_ACTION)
            .order_by(AuditEvent.id.desc()).limit(40).all())
    for e in latest:
        p=audit_payload(e)
        if p.get("enrichment_revision")==revision:
            return {"status":p.get("status","PENDING"),"reviewer_id":e.actor_id,
                    "reason":p.get("reason")}
    return {"status":"PENDING","reviewer_id":None,"reason":None}


def full_projection(db,campaign_id,result_id,assessment,source):
    """Current effective audit-only fields plus per-field provenance and history."""
    baseline={field:_baseline(field,source,assessment) for field in FIELDS}
    data={field:{"original":value,"effective":value,"basis":"ORIGINAL_SAVED",
                 "verification":"UNVERIFIED","event_id":0,"evidence_url":""}
          for field,value in baseline.items()}
    out={"revision":0,"fields":data,"history":[],"stale":False,
         "secondary_review_required":False,
         "secondary_review":{"status":"NOT_REQUIRED","reviewer_id":None,"reason":None}}
    if campaign_id!=QA_ID:return out
    rows=_recent(db,campaign_id,result_id)
    if not rows:return out
    out["revision"]=rows[0].id
    digest=source_integrity_digest(source)
    seen=set()
    for event in rows:
        p=audit_payload(event)
        stale=p.get("source_integrity_digest")!=digest or p.get("assessment_id")!=(assessment.id if assessment else None)
        if stale:out["stale"]=True
        patches=p.get("fields")
        if not isinstance(patches,list):continue
        for patch in patches:
            field=patch.get("field") if isinstance(patch,dict) else None
            if field not in FIELDS:continue
            if field in seen:continue
            seen.add(field)
            if not stale:
                data[field].update({
                    "effective":patch.get("value",""),"basis":"QA_OFFICER_ENRICHMENT",
                    "verification":patch.get("verification","UNVERIFIED"),
                    "event_id":event.id,"evidence_url":patch.get("evidence_url",""),
                })
        out["history"].append({
            "revision":event.id,"actor_id":event.actor_id,"at":event.occurred_at,
            "reason":p.get("reason"),"fields":patches or [],
            "stale":stale,
        })
    out["secondary_review_required"]=any(
        entry.get("field") in SENSITIVE
        for row in out["history"] if not row["stale"]
        for entry in row["fields"] if isinstance(entry,dict)
    )
    if out["secondary_review_required"]:
        out["secondary_review"]=second_review_state(db,campaign_id,result_id,out["revision"])
    return out


def _scope(db,user,campaign_id,result_id=None,write=False):
    from .inbox_human_gate import _read_enabled
    from .inbox_human_corrections import _authorize,can_edit_gate1
    _read_enabled()
    if result_id is not None:
        officer,campaign,source=_authorize(db,user,campaign_id,result_id,write)
    else:
        officer=_grant(db,user,"view_intelligence")
        campaign=_campaign(db,officer,campaign_id)
        source=None
        if write and not can_edit_gate1(officer,campaign):
            raise HTTPException(403,"Pilot authorization required")
    if not is_qa_campaign(campaign):
        raise HTTPException(403,"Full-field editing is only available in the Politk Uang QA pilot")
    return officer,campaign,source


@router.get("/campaign/{campaign_id}/source/{result_id}/full-review")
def full_review(campaign_id:int,result_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    officer,campaign,source=_scope(db,user,campaign_id,result_id)
    from .inbox_human_corrections import _latest_assessment,can_edit_gate1
    a=_latest_assessment(db,campaign_id,result_id)
    p=full_projection(db,campaign_id,result_id,a,source)
    can_write=can_edit_gate1(officer,campaign)
    from .inbox_gate_real_qa_v1867 import isolated_source
    return {"campaign_id":str(campaign_id),"result_id":str(result_id),
            "field_groups":{k:list(v) for k,v in FIELD_GROUPS.items()},
            **p,"can_edit":bool(can_write and isolated_source(db,campaign,source)),
            "qa_audit_only":True,"original_source_preserved":True,
            "no_publication":True,"no_model_training":True}


@router.post("/campaign/{campaign_id}/source/{result_id}/full-review")
def save_full_review(campaign_id:int,result_id:int,body:FullReviewBatch,
                     user:User=Depends(current_user),db:Session=Depends(get_db)):
    officer,campaign,source=_scope(db,user,campaign_id,result_id,True)
    from .inbox_human_corrections import _lock_current_source,_latest_assessment
    source=_lock_current_source(db,officer,source)
    a=_latest_assessment(db,campaign_id,result_id)
    if a is None or a.id!=body.expected_assessment_id:
        raise HTTPException(409,"Saved assessment changed; refresh")
    if source_integrity_digest(source)!=body.expected_source_digest:
        raise HTTPException(409,"Source changed; refresh")
    old=full_projection(db,campaign_id,result_id,a,source)
    if old["stale"] or old["revision"]!=body.expected_revision:
        raise HTTPException(409,"Field changes conflict with another review; refresh")
    patches=[];seen=set()
    for entry in body.fields:
        field=entry.field.strip()
        if field not in FIELDS or field in seen:
            raise HTTPException(422,"Unsupported or repeated field")
        seen.add(field)
        if entry.mode not in REASONS or entry.verification not in VERIFICATIONS:
            raise HTTPException(422,"Invalid correction mode or verification status")
        if entry.mode=="UNAVAILABLE" and entry.verification=="SOURCE_CONFIRMED":
            raise HTTPException(422,"Unavailable information cannot be source-confirmed")
        new="" if entry.mode=="UNAVAILABLE" else _value(field,entry.value)
        url=_safe_url(entry.evidence_url)
        if entry.verification=="SOURCE_CONFIRMED" and not url:
            raise HTTPException(422,"Source-confirmed fields require a supporting reference")
        if old["fields"][field]["effective"]==new:
            raise HTTPException(422,f"No change to {field}")
        patches.append({
            "field":field,"value":new,"previous":old["fields"][field]["effective"],
            "mode":entry.mode,"verification":entry.verification,
            "evidence_url":url,"field_reason":entry.field_reason.strip(),
            "high_impact":field in SENSITIVE,
        })
    event=AuditEvent(
        subject_type=GATE1_AUDIT_SUBJECT,subject_id=f"{QA_ID}:{result_id}",
        action=FULL_ACTION,actor_id=str(user.id),actor_name=str(officer.get("name") or "")[:255],
        changes_json=json.dumps({
            "campaign_id":QA_ID,"result_id":result_id,"field_name":"enrichment",
            "old_effective_value":"pre-enrichment","new_effective_value":f"{len(patches)} field(s) edited",
            "fields":patches,"reason":body.reason.strip(),
            "previous_revision":old["revision"],"source_integrity_digest":body.expected_source_digest,
            "assessment_id":a.id,"qa_audit_only":True,"original_source_preserved":True,
            "canonical_assessment_preserved":True,"model_training_triggered":False,
            "official_insight_published":False,
            "requires_secondary_review":any(p["high_impact"] for p in patches),
        },sort_keys=True,ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat())
    db.add(event);db.commit()
    return {"saved":True,"revision":event.id,"fields_saved":len(patches),
            "secondary_review_required":any(p["high_impact"] for p in patches),
            "qa_audit_only":True,"original_source_preserved":True,
            "canonical_assessment_preserved":True,"automatic_publication":False,
            "automatic_training":False}


@router.post("/campaign/{campaign_id}/source/{result_id}/full-review/secondary")
def secondary_review(campaign_id:int,result_id:int,body:SecondReviewIn,
                     user:User=Depends(current_user),db:Session=Depends(get_db)):
    officer,campaign,source=_scope(db,user,campaign_id,result_id,True)
    if not has(officer,"administration") or not has(officer,"human_validation"):
        raise HTTPException(403,"Administrator plus human validation permissions required")
    from .inbox_human_corrections import _lock_current_source,_latest_assessment
    source=_lock_current_source(db,officer,source)
    a=_latest_assessment(db,campaign_id,result_id)
    p=full_projection(db,campaign_id,result_id,a,source)
    if (not a or a.id!=body.expected_assessment_id or
        body.expected_source_digest!=source_integrity_digest(source) or
        p["stale"] or p["revision"]!=body.expected_revision):
        raise HTTPException(409,"Review snapshot changed; refresh")
    if not p["secondary_review_required"]:
        raise HTTPException(422,"No secondary review required")
    latest=_recent(db,campaign_id,result_id)
    if latest and str(latest[0].actor_id)==str(user.id):
        raise HTTPException(403,"A second officer must independently review these changes")
    if body.status not in ("APPROVED","REJECTED"):
        raise HTTPException(422,"Invalid secondary review decision")
    event=AuditEvent(
        subject_type=GATE1_AUDIT_SUBJECT,subject_id=f"{QA_ID}:{result_id}",
        action=SECOND_ACTION,actor_id=str(user.id),actor_name=str(officer.get("name") or "")[:255],
        changes_json=json.dumps({
            "enrichment_revision":p["revision"],"status":body.status,"reason":body.reason.strip(),
            "assessment_id":a.id,"source_integrity_digest":body.expected_source_digest,
            "qa_audit_only":True,"automatic_publication":False,
        },sort_keys=True,ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat())
    db.add(event);db.commit()
    return {"saved":True,"status":body.status,"secondary_revision":event.id,
            "automatic_publication":False}


def _manual_rows(db):
    return db.query(AuditEvent).filter_by(
        subject_type="Gate1ManualEvidenceQA",action=MANUAL_ACTION,
        subject_id=str(QA_ID)).order_by(AuditEvent.id.desc()).limit(60).all()


@router.get("/campaign/{campaign_id}/manual-intake")
def manual_intake_list(campaign_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    _scope(db,user,campaign_id)
    return {"items":[{
        "id":row.id,"created_at":row.occurred_at,"officer_id":row.actor_id,
        **{key:audit_payload(row).get(key) for key in
           ("platform","title","text_content","source_url","author_name","observed_at","reason","evidence_url")},
        "status":"QA_UNVERIFIED","official_intelligence":False,
    } for row in _manual_rows(db)],"qa_only":True,"not_provider_fetched":True,
       "no_automatic_publication":True}


@router.post("/campaign/{campaign_id}/manual-intake")
def manual_intake_create(campaign_id:int,body:ManualEvidenceIn,
                         user:User=Depends(current_user),db:Session=Depends(get_db)):
    officer,campaign,_=_scope(db,user,campaign_id,write=True)
    url=_safe_url(body.source_url)
    evidence=_safe_url(body.evidence_url)
    if not url and not evidence:
        raise HTTPException(422,"At least one original or supporting source URL is required")
    e=AuditEvent(
        subject_type="Gate1ManualEvidenceQA",subject_id=str(QA_ID),
        action=MANUAL_ACTION,actor_id=str(user.id),actor_name=str(officer.get("name") or "")[:255],
        changes_json=json.dumps({
            "campaign_id":QA_ID,"platform":body.platform.strip(),"title":body.title.strip(),
            "text_content":body.text_content.strip(),"source_url":url,
            "author_name":body.author_name.strip(),"observed_at":body.observed_at.strip(),
            "reason":body.reason.strip(),"evidence_url":evidence,
            "source_type":"OFFICER_SUPPLIED","verification":"UNVERIFIED",
            "qa_audit_only":True,"provider_response_fabricated":False,
            "official_intelligence_published":False,"model_training_triggered":False,
        },sort_keys=True,ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat())
    db.add(e);db.commit()
    return {"saved":True,"manual_evidence_id":e.id,"status":"QA_UNVERIFIED",
            "created_in_social_listening":False,"automatic_publication":False}
