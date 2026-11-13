"""Audited BAWASLU casework: human-routed assignments and evidence-led report drafts.

The AI/rule classification is advisory. A suggested province is NOT a
verified incident jurisdiction and cannot extend provincial data access.
"""
import json
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, and_, or_
from sqlalchemy.orm import Mapped, mapped_column, Session
from .db import Base, get_db
from .models import (User, AccessGrant, IntelligenceItem, EvidenceAssessment)
from .auth import current_user
from .access import profile, has, allowed, audit

router = APIRouter(prefix="/api/casework", tags=["casework"])
DEPARTMENTS = (
    "Pengawasan", "Penanganan Pelanggaran", "Hukum & Sengketa",
    "Humas & Hubungan Masyarakat", "Data & Analisis", "Sekretariat"
)
SCOPES = ("NATIONAL", "PROVINCE")
CASE_STATES = ("OPEN", "ASSIGNED", "IN_REVIEW", "NEEDS_INFORMATION", "CLOSED")
REPORT_STATES = ("DRAFT", "SUBMITTED", "RETURNED", "APPROVED")
SOURCE_REVIEW_STATES = ("SOURCE_CHECKED", "NEEDS_INFORMATION", "SOURCE_UNAVAILABLE")

class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_id: Mapped[str] = mapped_column(String(72), nullable=False)
    campaign_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    source_excerpt: Mapped[str] = mapped_column(Text, default="")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    suggested_provinces_json: Mapped[str] = mapped_column(Text, default="[]")
    verified_province: Mapped[str] = mapped_column(String(128), default="")
    originating_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    originating_province: Mapped[str] = mapped_column(String(128), default="")
    target_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    target_province: Mapped[str] = mapped_column(String(128), default="")
    target_department: Mapped[str] = mapped_column(String(120), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CaseTransition(Base):
    __tablename__ = "case_transitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case_assignments.id"), nullable=False, index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    happened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CaseReport(Base):
    __tablename__ = "case_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("case_assignments.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[str] = mapped_column(Text, default="")
    verification_notes: Mapped[str] = mapped_column(Text, default="")
    recommendations: Mapped[str] = mapped_column(Text, default="")
    source_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

def _json(value, fallback):
    try:
        result = json.loads(value or "")
        return result if isinstance(result, type(fallback)) else fallback
    except (ValueError, TypeError):
        return fallback

def _require(p, permission="view_intelligence"):
    if not has(p, permission):
        raise HTTPException(403, "You do not have permission for this casework action")

def _clean(value, maxlen=1500):
    return " ".join(str(value or "").split())[:maxlen]

def _team(p):
    return ("NATIONAL", "") if p.get("geographic_scope") == "Nationwide" else ("PROVINCE", p.get("province") or "")

def _visible(case, p, user_id):
    if not has(p, "view_intelligence"):
        return False
    if p.get("geographic_scope") == "Nationwide":
        return True
    province = p.get("province") or ""
    if p.get("geographic_scope") not in ("Nationwide", "Province"):
        return case.created_by == user_id or (
            case.assignee_id == user_id and case.verified_province == province)
    if not province:
        return False
    # No cross-province access. A province retains its outgoing escalations.
    return (case.originating_scope == "PROVINCE" and case.originating_province == province) or (
        case.target_scope == "PROVINCE" and case.target_province == province and
        case.verified_province == province
    )

def _authorized_cases_query(db, p, user_id):
    """Apply geographical visibility in SQL before bounded officer queue reads.

    This mirrors _visible; callers retain _visible as a second protection.
    """
    q = db.query(CaseAssignment)
    scope = p.get("geographic_scope")
    province = p.get("province") or ""
    if scope == "Nationwide":
        return q
    if scope == "Province":
        if not province:
            return q.filter(CaseAssignment.id == -1)
        return q.filter(or_(
            and_(CaseAssignment.originating_scope == "PROVINCE",
                 CaseAssignment.originating_province == province),
            and_(CaseAssignment.target_scope == "PROVINCE",
                 CaseAssignment.target_province == province,
                 CaseAssignment.verified_province == province)))
    return q.filter(or_(
        CaseAssignment.created_by == user_id,
        and_(CaseAssignment.assignee_id == user_id,
             CaseAssignment.verified_province == province)))


def _current_report_ids(db, case_ids):
    """Return latest audit report version for each permitted case."""
    if not case_ids:
        return {}
    rows = db.query(CaseReport).filter(CaseReport.case_id.in_(case_ids)).order_by(
        CaseReport.created_at.desc(), CaseReport.id.desc()).all()
    latest = {}
    for report in rows:
        latest.setdefault(report.case_id, report)
    return latest


def _editable(case, p, user_id):
    return _visible(case, p, user_id) and has(p, "add_intelligence") and (
        p.get("geographic_scope") == "Nationwide" or case.created_by == user_id or
        case.assignee_id == user_id or (
            case.target_scope == "PROVINCE" and case.target_province == p.get("province")
        )
    )

def _receiving_officer(case, p, user_id):
    """Only the intended receiving team can take ownership of an assignment.

    The originating team's retained read visibility is not permission to accept
    work on behalf of its destination. An individually assigned case cannot
    be claimed by a different officer.
    """
    if p.get("geographic_scope") not in ("Nationwide","Province"):
        return False
    if not has(p,"add_intelligence") or case.status not in ("OPEN","ASSIGNED"):
        return False
    if not _visible(case,p,user_id):
        return False
    scope,province=_team(p)
    if scope != case.target_scope or (scope=="PROVINCE" and (
        case.target_province != province or case.verified_province != province)):
        return False
    return case.assignee_id is None or case.assignee_id==user_id


def _assignee(db, target_scope, province, user_id):
    if user_id is None:
        return None
    user = db.get(User, user_id)
    grant = db.query(AccessGrant).filter_by(user_id=user_id).one_or_none()
    if not user or not grant or grant.status != "Active":
        raise HTTPException(422, "Selected officer is not active")
    perms = _json(grant.permissions_json, {})
    if not (perms.get("view_intelligence") is True and (
        perms.get("add_intelligence") is True or perms.get("human_validation") is True)):
        raise HTTPException(422, "Selected officer cannot manage intelligence")
    if target_scope == "NATIONAL" and grant.geographic_scope != "Nationwide":
        raise HTTPException(422, "Select an officer from the national team")
    if target_scope == "PROVINCE" and (
        grant.geographic_scope != "Province" or grant.province != province
    ):
        raise HTTPException(422, "Select an officer from the requested province")
    return user.id

def _validate_route(case_or_source, p, scope, province):
    if scope not in SCOPES:
        raise HTTPException(422, "Invalid receiving team")
    if scope == "NATIONAL":
        return ""
    verified = case_or_source.get("verified_province", "") if isinstance(case_or_source, dict) else case_or_source.verified_province
    if not verified or province != verified:
        raise HTTPException(422, "A human-confirmed incident province is required for provincial assignment")
    if p.get("geographic_scope") != "Nationwide" and province != p.get("province"):
        raise HTTPException(403, "Cannot transfer a case to another province")
    return province

def _source(db, p, source_type, source_id, campaign_id):
    from .processing_hints import source_hints, normalize_candidate_signals
    from .candidate_registry import candidate_index, resolve_post_candidate_mentions
    text = ""
    tags = []
    provinces = []
    verified = ""
    url = ""
    title = ""
    if source_type == "SOCIAL":
        from .jurisdiction_review import scoped_post, jurisdiction_status
        if not campaign_id or not str(campaign_id).isdigit():
            raise HTTPException(422, "Choose the campaign for this social post")
        try:
            campaign, post, relevant = scoped_post(db, p, campaign_id, source_id)
        except (PermissionError, ValueError) as e:
            raise HTTPException(403, "Source post is unavailable in your authorized scope") from e
        if not relevant:
            raise HTTPException(422, "A relevant saved assessment is needed to start casework")
        assessment = db.query(EvidenceAssessment).filter_by(
            campaign_id=campaign.id, result_id=post.id
        ).order_by(EvidenceAssessment.assessment_version.desc(), EvidenceAssessment.id.desc()).first()
        text = post.text_content or ""
        url = post.canonical_url or ""
        title = _clean(text, 170)
        values = _json(assessment.candidate_signals_json, []) if assessment else []
        matches = resolve_post_candidate_mentions(values, text, candidate_index(db, p))
        candidates = [x.get("canonical_name") or x.get("source_name") for x in matches if x.get("canonical_name") or x.get("source_name")]
        candidates = normalize_candidate_signals(candidates)
        for name in candidates[:8]:
            tags.append({"type":"CANDIDATE","label":name,"basis":"SAVED_AI_OR_EXPLICIT_MENTION","verified":False})
        issues = _json(assessment.potential_issue_signals_json, []) if assessment else []
        topic_labels = _json(assessment.topic_labels_json, []) if assessment else []
        location = jurisdiction_status(db, campaign.id, post.id, post)
        verified = location.get("incident_province") if location.get("incident_jurisdiction_verified") else ""
    elif source_type == "INTELLIGENCE":
        item = db.query(IntelligenceItem).filter_by(intelligence_id=source_id).first()
        if not item or not allowed(p,item):
            raise HTTPException(403, "Intelligence record unavailable")
        text = item.original_content or item.ai_summary or item.title or ""
        title = _clean(item.title or text,170)
        url = item.source_url or ""
        values = _json(item.related_entities_json, [])
        candidates = normalize_candidate_signals(values)
        for name in candidates[:8]:
            tags.append({"type":"CANDIDATE","label":name,"basis":"SAVED_ENTITY_SIGNAL","verified":False})
        issues = [item.potential_issue_category] if item.potential_issue_category else []
        topic_labels = _json(item.related_topics_json, [])
        verified = item.province if item.jurisdiction_confirmed else ""
    else:
        raise HTTPException(422, "Source must be SOCIAL or INTELLIGENCE")
    hints = source_hints(text)
    incident_provinces = hints.get("incident_location_cues_unverified") or []
    provinces = sorted(set(incident_provinces + (hints.get("province_mentions") or [])))
    for name in provinces[:8]:
        tags.append({"type":"PROVINCE","label":name,
                     "basis":"INCIDENT_TEXT_HINT" if name in incident_provinces else "PROVINCE_MENTION_ONLY",
                     "verified":name == verified})
    if verified and verified not in provinces:
        tags.append({"type":"PROVINCE","label":verified,"basis":"OFFICER_CONFIRMED","verified":True})
    if issues or hints.get("issue_screening",{}).get("needs_human_validation"):
        tags.append({"type":"SUSPECTED_VIOLATION","label":"Requires screening","basis":"SAVED_AI_OR_RULE_HINT","verified":False})
    merged = " ".join([text, json.dumps(topic_labels,ensure_ascii=False)]).casefold()
    if "bawaslu" in merged or any("bawaslu" in str(x).casefold() for x in topic_labels):
        tags.append({"type":"BAWASLU_ISSUE","label":"Institutional oversight","basis":"TEXT_OR_TOPIC_SIGNAL","verified":False})
    if any(x in merged for x in ("pemilu","pilkada","kpu","pencalonan","daftar pemilih","pemilihan","electoral")) or any("electoral" in str(x).casefold() for x in topic_labels):
        tags.append({"type":"ELECTORAL_ISSUE","label":"Electoral process","basis":"TEXT_OR_TOPIC_SIGNAL","verified":False})
    # Prevent duplicate labels across noisy assessment versions.
    unique = []
    seen = set()
    for tag in tags:
        key = (tag["type"],tag["label"].casefold())
        if key not in seen:
            seen.add(key)
            unique.append(tag)
    tag_types={tag["type"] for tag in unique}
    recommended_department=(
        "Penanganan Pelanggaran" if "SUSPECTED_VIOLATION" in tag_types
        else "Pengawasan" if "ELECTORAL_ISSUE" in tag_types
        else "Humas & Hubungan Masyarakat" if "BAWASLU_ISSUE" in tag_types
        else "Data & Analisis"
    )
    return {
        "recommended_department": recommended_department,
        "recommendation_basis": "Suggested from saved classification and source context; officer chooses the final destination.",
        "source_type":source_type,"source_id":str(source_id),
        "campaign_id":int(campaign_id) if source_type=="SOCIAL" else None,
        "title":title,"excerpt":text[:950],"source_url":url,
        "tags":unique[:20],"suggested_provinces":provinces[:8],
        "verified_province":verified,"status_explanation":"Tags are suggestions; officer review is required."
    }

def _case_view(case):
    return {
        "id":case.id,"title":case.title,"source_type":case.source_type,
        "source_id":case.source_id,"campaign_id":case.campaign_id,
        "source_url":case.source_url,"source_excerpt":case.source_excerpt,
        "tags":_json(case.tags_json,[]),"suggested_provinces":_json(case.suggested_provinces_json,[]),
        "verified_province":case.verified_province,
        "originating_scope":case.originating_scope,"originating_province":case.originating_province,
        "target_scope":case.target_scope,"target_province":case.target_province,
        "target_department":case.target_department,"assignee_id":case.assignee_id,
        "created_by":case.created_by,"status":case.status,"notes":case.notes,
        "created_at":case.created_at.isoformat(),"updated_at":case.updated_at.isoformat()
    }

def _report_view(report):
    return {
        "id":report.id,"case_id":report.case_id,"title":report.title,
        "executive_summary":report.executive_summary,"findings":report.findings,
        "verification_notes":report.verification_notes,"recommendations":report.recommendations,
        "source_snapshot":_json(report.source_snapshot_json,{}),
        "status":report.status,"created_by":report.created_by,
        "reviewed_by":report.reviewed_by,"review_comment":report.review_comment,
        "created_at":report.created_at.isoformat(),"updated_at":report.updated_at.isoformat()
    }

def _acceptance_trace(case, transitions, reports):
    """Evidence-linked procedural trace, NOT certification of a legal conclusion.

    Only an affirmative latest source-check, acknowledged receiving officer,
    current-report submission, and an independent recorded approval qualify.
    A missing event cannot be inferred from a mutable status alone.
    """
    events=list(transitions)
    latest_report=reports[0] if reports else None
    def event_for(action, report_id=None):
        return next((event for event in reversed(events)
            if event.action==action and (report_id is None or
                _json(event.details_json,{}).get("report_id")==report_id)),None)
    created=event_for("CREATED") or event_for("ASSISTANT_HANDOFF")
    acknowledged=event_for("ACKNOWLEDGED")
    routed=event_for("ROUTED")
    accepted=bool(acknowledged and (not routed or acknowledged.id>routed.id))
    latest_review=event_for("SOURCE_REVIEW_RECORDED")
    review_data=_json(latest_review.details_json,{}) if latest_review else {}
    source_checked=bool(
        latest_review and review_data.get("status")=="SOURCE_CHECKED"
        and review_data.get("original_source_opened") is True
        and review_data.get("source_type")==case.source_type
        and str(review_data.get("source_id"))==str(case.source_id)
        and review_data.get("source_url")==case.source_url)
    report_id=latest_report.id if latest_report else None
    submitted=bool(latest_report and latest_report.status in ("SUBMITTED","APPROVED")
        and event_for("REPORT_SUBMITTED",report_id))
    approved=bool(latest_report and latest_report.status=="APPROVED"
        and latest_report.reviewed_by and latest_report.reviewed_by!=latest_report.created_by
        and event_for("REPORT_APPROVED",report_id))
    steps=[
        ("source_linked",bool(created and case.source_id and case.source_url)),
        ("receiving_officer_accepted",accepted),
        ("original_source_checked",source_checked),
        ("latest_report_submitted",submitted),
        ("independent_report_approval",approved),
    ]
    completed=sum(1 for _,done in steps if done)
    return {
        "steps":[{"key":key,"done":done} for key,done in steps],
        "completed":completed,"total":len(steps),
        "workflow_trace_complete":completed==len(steps),
        "latest_source_review_status":review_data.get("status") if latest_review else None,
        "latest_source_review_note":review_data.get("note") if latest_review else None,
        "latest_report_id":report_id,
        "event_window_limited":len(events)>=200,
        "report_window_limited":len(reports)>=50,
        "evidence_source_is_confirmed_true":False,
        "legal_violation_determined":False,
        "client_acceptance_certified":False,
        "source_of_truth":"EXISTING_CASE_TRANSITIONS_AND_LATEST_CASE_REPORT",
        "paid_provider_called":False,
    }


def _record_event(db, case, user_id, action, details):
    db.add(CaseTransition(case_id=case.id,actor_id=user_id,action=action,
                          details_json=json.dumps(details,ensure_ascii=False)))
    db.commit()

class NewCase(BaseModel):
    source_type: str
    source_id: str
    campaign_id: int | None = None
    title: str = Field(default="", max_length=240)
    department: str
    target_scope: str = "NATIONAL"
    target_province: str = ""
    assignee_id: int | None = None
    notes: str = Field(default="",max_length=2400)

class RouteCase(BaseModel):
    department: str
    target_scope: str
    target_province: str = ""
    assignee_id: int | None = None
    note: str = Field(min_length=8,max_length=1500)

class CaseState(BaseModel):
    status: str
    note: str = Field(min_length=8,max_length=1500)

class ReportDraft(BaseModel):
    title: str = Field(min_length=5,max_length=240)
    executive_summary: str = Field(default="",max_length=5000)
    findings: str = Field(default="",max_length=10000)
    verification_notes: str = Field(default="",max_length=8000)
    recommendations: str = Field(default="",max_length=8000)

class ReportAction(BaseModel):
    status: str
    review_comment: str = Field(default="",max_length=2000)

class SourceReviewAction(BaseModel):
    status: str
    note: str = Field(min_length=20,max_length=1500)
    original_source_opened: bool = False

@router.get("/pilot-intake")
def pilot_intake(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """On-demand, read-only officer intake suggestions from existing Inbox.

    No crawling, new AI inference, case assignment, human sign-off or mutation.
    Every source link opens the existing casework preview, which rechecks
    original source authorization and jurisdiction at action time.
    """
    from .inbox_radar import live_inbox_findings
    from .officer_pilot_intake import officer_pilot_candidates
    p=profile(db,user)
    _require(p,"add_intelligence")
    findings,_=live_inbox_findings(db,p)
    preview=officer_pilot_candidates(findings,limit=12)
    source_ids=[row["source_id"] for row in preview["items"]]
    visible=[]
    if source_ids:
        candidates=(_authorized_cases_query(db,p,user.id)
            .filter(CaseAssignment.source_type=="SOCIAL",
                    CaseAssignment.source_id.in_(source_ids))
            .order_by(CaseAssignment.id.desc()).limit(250).all())
        visible=[case for case in candidates if _visible(case,p,user.id)]
    result=officer_pilot_candidates(findings,visible,limit=12)
    result["visible_case_lookup_limit"]=250
    result["requires_officer_permission"]="add_intelligence"
    result["permission_checked_at_request"]=True
    result["inbox_source_rescoped_on_action"]=True
    return result


@router.get("/options")
def options(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = profile(db,user)
    _require(p)
    scope, province = _team(p)
    officers = []
    for grant, candidate in db.query(AccessGrant,User).join(User,User.id == AccessGrant.user_id).filter(AccessGrant.status=="Active").limit(500).all():
        if grant.geographic_scope not in ("Nationwide","Province"):
            continue
        perms = _json(grant.permissions_json,{})
        if perms.get("view_intelligence") is not True or not (perms.get("add_intelligence") is True or perms.get("human_validation") is True):
            continue
        if scope == "PROVINCE" and grant.geographic_scope != "Nationwide" and grant.province != province:
            continue
        officers.append({"id":candidate.id,"name":candidate.full_name or candidate.email,
                         "scope":"NATIONAL" if grant.geographic_scope=="Nationwide" else "PROVINCE",
                         "province":grant.province})
    return {"departments":list(DEPARTMENTS),"officers":officers,"user_scope":scope,"user_province":province,
            "can_create":has(p,"add_intelligence"),"can_approve":has(p,"human_validation"),
            "current_user_id":user.id}

@router.get("/preview")
def preview(source_type: str, source_id: str, campaign_id: int | None = None,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = profile(db,user)
    _require(p)
    return _source(db,p,source_type.upper(),source_id,campaign_id)

def _queue_flags(case,p,user_id,reviewable_ids):
    active=case.status!="CLOSED"
    team,province=_team(p)
    receiving=(case.target_scope==team and (
        team=="NATIONAL" or case.target_province==province))
    return {
      "assigned_to_me":active and case.assignee_id==user_id,
      "team_unassigned":active and case.assignee_id is None and receiving,
      "needs_my_review":case.id in reviewable_ids,
      "sent_by_me":case.created_by==user_id,
      "received_from_other_team":active and receiving and (
          case.originating_scope!=case.target_scope or
          (team=="PROVINCE" and case.originating_province!=province)),
    }

@router.get("/cases")
def list_cases(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = profile(db,user)
    _require(p)
    cases = _authorized_cases_query(db,p,user.id).order_by(
        CaseAssignment.updated_at.desc(),CaseAssignment.id.desc()).limit(300).all()
    visible=[c for c in cases if _visible(c,p,user.id)]
    ids=[c.id for c in visible]
    latest=_current_report_ids(db,ids) if has(p,"human_validation") else {}
    reviewable={case_id for case_id,report in latest.items()
                if report.status=="SUBMITTED" and report.created_by!=user.id}
    rows=[]
    counters={"all":0,"assigned_to_me":0,"team_unassigned":0,
              "needs_my_review":0,"sent_by_me":0,"received_from_other_team":0}
    for case in visible:
        flags=_queue_flags(case,p,user.id,reviewable)
        view=_case_view(case)
        view["queue_flags"]=flags
        view["can_acknowledge"]=_receiving_officer(case,p,user.id)
        rows.append(view)
        counters["all"]+=1
        for key,value in flags.items():
            counters[key]+=int(value)
    return {"cases":rows,"queue_counts":counters,
            "current_team":{"scope":_team(p)[0],"province":_team(p)[1]},
            "can_review_reports":has(p,"human_validation"),
            "report_status_basis":"LATEST_REPORT_VERSION_PER_CASE",
            "query_scope":"SQL_AND_CASEWORK_VISIBILITY",
            "queue_window_limit":300,
            "queue_is_sample":len(visible)==300,
            "paid_provider_called":False}

@router.post("/cases")
def create_case(body: NewCase, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = profile(db,user)
    _require(p,"add_intelligence")
    if body.department not in DEPARTMENTS:
        raise HTTPException(422,"Choose a valid department")
    source = _source(db,p,body.source_type.upper(),body.source_id,body.campaign_id)
    dest_province = _validate_route(source,p,body.target_scope,body.target_province)
    assignee = _assignee(db,body.target_scope,dest_province,body.assignee_id)
    # Lock the initiating user's row (Postgres SELECT FOR UPDATE) so two
    # simultaneous clicks by this officer cannot each create the same
    # assignment. SQLite ignores this lock during isolated tests.
    db.query(User).filter(User.id==user.id).with_for_update().first()
    # Duplicate detection runs AFTER authorization and source revalidation.
    # Reuse only an active, currently VISIBLE case linked to the exact
    # saved source/campaign, never return an unrelated hidden case ID.
    active_candidates=(_authorized_cases_query(db,p,user.id)
        .filter(CaseAssignment.source_type==source["source_type"],
                CaseAssignment.source_id==source["source_id"],
                CaseAssignment.campaign_id==source["campaign_id"],
                CaseAssignment.status!="CLOSED")
        .order_by(CaseAssignment.id.desc()).limit(50).all())
    existing=next((case for case in active_candidates if _visible(case,p,user.id)),None)
    if existing is not None:
        return {**_case_view(existing),"existing":True,"assignment_created":False}
    origin_scope,origin_province = _team(p)
    item = CaseAssignment(
        title=_clean(body.title,240) or source["title"] or "Casework item",
        source_type=source["source_type"], source_id=source["source_id"],
        campaign_id=source["campaign_id"],source_url=source["source_url"],
        source_excerpt=source["excerpt"],tags_json=json.dumps(source["tags"],ensure_ascii=False),
        suggested_provinces_json=json.dumps(source["suggested_provinces"],ensure_ascii=False),
        verified_province=source["verified_province"] or "",
        originating_scope=origin_scope,originating_province=origin_province,
        target_scope=body.target_scope,target_province=dest_province,
        target_department=body.department,assignee_id=assignee,
        created_by=user.id,status="ASSIGNED" if assignee else "OPEN",notes=body.notes
    )
    db.add(item)
    db.flush()
    _record_event(db,item,user.id,"CREATED",{"scope":body.target_scope,"department":body.department,"assignee_id":assignee})
    audit(db,p,"CaseAssignment",item.id,"CASE_CREATED",{"target_scope":body.target_scope,"department":body.department})
    return {**_case_view(item),"existing":False,"assignment_created":True}

@router.get("/cases/{case_id}")
def case_detail(case_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = profile(db,user)
    _require(p)
    case = db.get(CaseAssignment,case_id)
    if not case or not _visible(case,p,user.id):
        raise HTTPException(404,"Case not found")
    # Read the latest 200 audit events, not the oldest 200. Re-sort the
    # selected window into chronological order for _acceptance_trace.
    transitions = list(reversed(db.query(CaseTransition).filter_by(case_id=case_id)
        .order_by(CaseTransition.id.desc()).limit(200).all()))
    reports = db.query(CaseReport).filter_by(case_id=case_id).order_by(
        CaseReport.created_at.desc(),CaseReport.id.desc()).limit(50).all()
    report_views=[]
    for index,report in enumerate(reports):
        item=_report_view(report)
        item["is_latest_version"]=(index==0)
        report_views.append(item)
    return {"case":_case_view(case),"events":[{"id":x.id,"action":x.action,"actor_id":x.actor_id,
            "details":_json(x.details_json,{}),"at":x.happened_at.isoformat()} for x in transitions],
            "reports":report_views,"can_edit":_editable(case,p,user.id),
            "can_approve":has(p,"human_validation"),
            "can_record_source_review":(_editable(case,p,user.id)
                and case.assignee_id==user.id and case.status=="IN_REVIEW"),
            "workflow_trace":_acceptance_trace(case,transitions,reports),
            "can_acknowledge":_receiving_officer(case,p,user.id)}

@router.post("/cases/{case_id}/acknowledge")
def acknowledge_case(case_id:int,user:User=Depends(current_user),
                     db:Session=Depends(get_db)):
    """Receiving-officer one-click acceptance; never changes legal findings."""
    p=profile(db,user)
    _require(p,"add_intelligence")
    case=db.query(CaseAssignment).filter_by(id=case_id).with_for_update().one_or_none()
    if not case or not _visible(case,p,user.id):
        raise HTTPException(404,"Case not found")
    if not _receiving_officer(case,p,user.id):
        raise HTTPException(403,"Only the assigned officer or authorized receiving team can accept this case")
    if case.assignee_id is None:
        case.assignee_id=user.id
    before=case.status
    case.status="IN_REVIEW"
    case.updated_at=datetime.utcnow()
    _record_event(db,case,user.id,"ACKNOWLEDGED",{
        "previous_status":before,"assigned_to":user.id,
        "scope":case.target_scope,"province":case.target_province,
        "note":"Receiving officer accepted and started review"})
    audit(db,p,"CaseAssignment",case.id,"CASE_ACKNOWLEDGED",{
        "before":before,"after":"IN_REVIEW","assigned_to":user.id})
    return _case_view(case)


@router.post("/cases/{case_id}/source-review")
def record_source_review(case_id: int, body: SourceReviewAction,
                         user: User=Depends(current_user),
                         db: Session=Depends(get_db)):
    """Human source-access attestation. This is NOT a factual/legal verdict."""
    p=profile(db,user)
    _require(p,"add_intelligence")
    case=db.query(CaseAssignment).filter_by(id=case_id).with_for_update().one_or_none()
    if not case or not _visible(case,p,user.id):
        raise HTTPException(404,"Case not found")
    if not _editable(case,p,user.id) or case.status!="IN_REVIEW" or case.assignee_id!=user.id:
        raise HTTPException(403,"Only the current receiving officer may record source review")
    if body.status not in SOURCE_REVIEW_STATES:
        raise HTTPException(422,"Invalid source review state")
    if len(body.note.strip())<20:
        raise HTTPException(422,"Explain the source review in at least 20 characters")
    if body.status=="SOURCE_CHECKED" and (
        not body.original_source_opened or not case.source_url.startswith(("https://","http://"))):
        raise HTTPException(422,"Open the saved original source URL before attesting a source check")
    details={
        "status":body.status,"note":body.note.strip(),
        "original_source_opened":bool(body.original_source_opened),
        "source_type":case.source_type,"source_id":case.source_id,
        "campaign_id":case.campaign_id,"source_url":case.source_url,
        "not_a_content_or_legal_verdict":True,
    }
    case.updated_at=datetime.utcnow()
    _record_event(db,case,user.id,"SOURCE_REVIEW_RECORDED",details)
    audit(db,p,"CaseAssignment",case.id,"SOURCE_REVIEW_RECORDED",{
        "source_type":case.source_type,"source_id":case.source_id,
        "status":body.status,"original_source_opened":body.original_source_opened})
    return {"case_id":case.id,"status":body.status,
            "original_source_opened":body.original_source_opened,
            "requires_separate_legal_assessment":True,
            "officer_id":user.id,"paid_provider_called":False}


@router.post("/cases/{case_id}/route")
def route_case(case_id: int,body: RouteCase,user: User=Depends(current_user),db: Session=Depends(get_db)):
    p=profile(db,user)
    case=db.get(CaseAssignment,case_id)
    if not case or not _editable(case,p,user.id):
        raise HTTPException(403,"Not authorized to route this case")
    if case.status == "CLOSED":
        raise HTTPException(409,"Closed cases cannot be reassigned")
    if body.department not in DEPARTMENTS:
        raise HTTPException(422,"Choose a valid department")
    province=_validate_route(case,p,body.target_scope,body.target_province)
    assignee=_assignee(db,body.target_scope,province,body.assignee_id)
    before={"scope":case.target_scope,"province":case.target_province,"department":case.target_department,
            "assignee_id":case.assignee_id}
    case.target_scope=body.target_scope
    case.target_province=province
    case.target_department=body.department
    case.assignee_id=assignee
    case.status="ASSIGNED" if assignee else "OPEN"
    case.updated_at=datetime.utcnow()
    _record_event(db,case,user.id,"ROUTED",{"before":before,"after":{"scope":case.target_scope,
        "province":province,"department":body.department,"assignee_id":assignee},"note":body.note})
    audit(db,p,"CaseAssignment",case.id,"CASE_ROUTED",{"before":before,"target_scope":case.target_scope})
    return _case_view(case)

@router.post("/cases/{case_id}/status")
def change_status(case_id: int,body: CaseState,user: User=Depends(current_user),db: Session=Depends(get_db)):
    p=profile(db,user)
    case=db.get(CaseAssignment,case_id)
    if not case or not _editable(case,p,user.id):
        raise HTTPException(403,"Not authorized to change this case")
    if body.status not in CASE_STATES:
        raise HTTPException(422,"Invalid case status")
    if case.status=="CLOSED":
        raise HTTPException(409,"Closed cases are read-only")
    if body.status=="CLOSED" and not has(p,"human_validation"):
        raise HTTPException(403,"Human validation permission is required to close a case")
    previous=case.status
    case.status=body.status
    case.updated_at=datetime.utcnow()
    _record_event(db,case,user.id,"STATUS_CHANGED",{"from":previous,"to":body.status,"note":body.note})
    audit(db,p,"CaseAssignment",case.id,"CASE_STATUS_CHANGED",{"from":previous,"to":body.status})
    return _case_view(case)

@router.post("/cases/{case_id}/reports")
def create_report(case_id: int,body: ReportDraft,user: User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    case=db.get(CaseAssignment,case_id)
    if not case or not _editable(case,p,user.id):
        raise HTTPException(403,"Not authorized to create a report for this case")
    snapshot={"case_id":case.id,"source_type":case.source_type,"source_id":case.source_id,
        "campaign_id":case.campaign_id,"source_url":case.source_url,
        "tags":_json(case.tags_json,[]),"verified_province":case.verified_province,
        "captured_at":datetime.now(timezone.utc).isoformat()}
    report=CaseReport(case_id=case.id,title=body.title,executive_summary=body.executive_summary,
        findings=body.findings,verification_notes=body.verification_notes,
        recommendations=body.recommendations,source_snapshot_json=json.dumps(snapshot,ensure_ascii=False),
        status="DRAFT",created_by=user.id)
    db.add(report);db.flush()
    _record_event(db,case,user.id,"REPORT_DRAFTED",{"report_id":report.id})
    audit(db,p,"CaseReport",report.id,"REPORT_CREATED",{"case_id":case.id})
    return _report_view(report)

@router.post("/cases/{case_id}/reports/ai-draft")
def ai_report_draft(case_id: int,user: User=Depends(current_user),db: Session=Depends(get_db)):
    """Explicit, one-request AI assistance; never automatically bill on case creation."""
    p=profile(db,user)
    case=db.get(CaseAssignment,case_id)
    if not case or not _editable(case,p,user.id):
        raise HTTPException(403,"Not authorized to draft a report")
    from .assistant_orchestration import generate
    from .intelligence_assistant import AssistantProviderError
    evidence=[{
        "record_id":("SOCIAL-" if case.source_type=="SOCIAL" else "")+case.source_id,
        "record_type":"SOCIAL_LISTENING" if case.source_type=="SOCIAL" else "FORMAL_INTELLIGENCE",
        "title":case.title,"source_excerpt":case.source_excerpt[:950],
        "source_url":case.source_url,"verification_status":"REVIEW_REQUIRED",
        "topic_labels":[tag.get("label") for tag in _json(case.tags_json,[]) if isinstance(tag,dict)],
    }]
    instruction=(
        "Susun draf laporan analisis intelijen untuk penelaahan BAWASLU atas sumber berikut. "
        "Uraikan temuan faktual, dugaan yang belum diverifikasi, implikasi pengawasan yang netral, "
        "bukti primer yang harus dibandingkan, dan rekomendasi penugasan yang bersyarat. "
        "Jangan menyimpulkan pelanggaran atau mengklaim kepastian hukum tanpa sumber resmi. "
        "Keluarkan ringkasan eksekutif, temuan, batas bukti dan langkah verifikasi yang konkret."
    )
    try:
        answer, cited, meta = generate(instruction, "", evidence, "GROUNDED",
                                       response_depth="DEEP")
    except AssistantProviderError as exc:
        raise HTTPException(503,"AI drafting unavailable. Your case remains saved.") from exc
    if not answer.strip():
        raise HTTPException(503,"AI drafting returned no usable text")
    checks=(meta.get("analytical_findings") or {}).get("review_steps") or []
    snapshot={
        "case_id":case.id,"source_type":case.source_type,"source_id":case.source_id,
        "source_url":case.source_url,"draft_origin":"AI_ASSISTED_REQUIRES_HUMAN_REVIEW",
        "cited_ids":cited,"created_at":datetime.now(timezone.utc).isoformat()
    }
    # Preserve the provenance distinction while keeping internal enums out of text.
    def readable(text):
        return str(text or "").replace("UNVERIFIED_SOCIAL_SOURCE","sumber belum diverifikasi").replace(
            "AI_RELEVANCE_NOT_LEGAL_VERIFICATION","relevansi belum menjadi kesimpulan hukum")
    report=CaseReport(case_id=case.id,title=("Draf analisis: "+case.title)[:240],
        executive_summary=readable(answer.split("\n")[0])[:3000],findings=readable(answer)[:9500],
        verification_notes="Satu sumber yang ditautkan belum merupakan verifikasi independen. "
          "Bandingkan dokumen sumber primer, konteks tanggal, atribusi dan yurisdiksi sebelum diserahkan.",
        recommendations="\n".join(str(x) for x in checks[:5])[:7000],
        source_snapshot_json=json.dumps(snapshot,ensure_ascii=False),
        status="DRAFT",created_by=user.id)
    db.add(report)
    db.flush()
    _record_event(db,case,user.id,"AI_REPORT_DRAFTED",{"report_id":report.id,"source_id":case.source_id,
        "requires_human_review":True})
    audit(db,p,"CaseReport",report.id,"AI_DRAFT_CREATED",{"case_id":case.id})
    return _report_view(report)

@router.put("/reports/{report_id}")
def update_report(report_id: int,body: ReportDraft,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    report=db.get(CaseReport,report_id)
    case=db.get(CaseAssignment,report.case_id) if report else None
    if not case or not _editable(case,p,user.id) or report.status not in ("DRAFT","RETURNED"):
        raise HTTPException(403,"Report is not editable")
    latest=(db.query(CaseReport.id).filter_by(case_id=case.id)
        .order_by(CaseReport.created_at.desc(),CaseReport.id.desc()).first())
    if latest and int(latest[0])!=report.id:
        raise HTTPException(409,"A newer report exists; edit the latest report instead")
    report.title=body.title
    report.executive_summary=body.executive_summary
    report.findings=body.findings
    report.verification_notes=body.verification_notes
    report.recommendations=body.recommendations
    report.updated_at=datetime.utcnow()
    _record_event(db,case,user.id,"REPORT_EDITED",{"report_id":report.id})
    return _report_view(report)

@router.post("/reports/{report_id}/transition")
def transition_report(report_id:int,body:ReportAction,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    report=db.query(CaseReport).filter_by(id=report_id).with_for_update().one_or_none()
    case=db.get(CaseAssignment,report.case_id) if report else None
    if not case or not _visible(case,p,user.id):
        raise HTTPException(404,"Report not found")
    latest=(db.query(CaseReport.id).filter_by(case_id=case.id)
        .order_by(CaseReport.created_at.desc(),CaseReport.id.desc()).first())
    if latest and int(latest[0])!=report.id:
        raise HTTPException(409,"A newer report exists; open the latest report for review")
    action=body.status
    if action=="SUBMITTED":
        if not _editable(case,p,user.id) or report.status not in ("DRAFT","RETURNED"):
            raise HTTPException(403,"Only an authorized officer can submit a draft")
        if not report.findings.strip() or not report.verification_notes.strip():
            raise HTTPException(422,"Findings and verification notes are required before submission")
    elif action in ("RETURNED","APPROVED"):
        if not has(p,"human_validation") or report.status!="SUBMITTED":
            raise HTTPException(403,"Officer review permission and a submitted report are required")
        if report.created_by==user.id:
            raise HTTPException(403,"A report cannot be approved by its own author")
        if action=="RETURNED" and len(body.review_comment.strip())<8:
            raise HTTPException(422,"Provide a reason for returning this report")
        report.reviewed_by=user.id
    else:
        raise HTTPException(422,"Unsupported report transition")
    previous=report.status
    report.status=action
    report.review_comment=body.review_comment
    report.updated_at=datetime.utcnow()
    _record_event(db,case,user.id,"REPORT_"+action,{"report_id":report.id,"previous":previous,"note":body.review_comment})
    audit(db,p,"CaseReport",report.id,"REPORT_"+action,{"case_id":case.id})
    return _report_view(report)


class AssistantHandoff(BaseModel):
    """A human-confirmed case+draft handoff, reusing an already generated answer."""
    source_type: str = Field(min_length=3,max_length=32)
    source_id: str = Field(min_length=1,max_length=72)
    campaign_id: int | None = None
    department: str
    target_scope: str = "NATIONAL"
    target_province: str = ""
    assignee_id: int | None = None
    title: str = Field(default="",max_length=240)
    executive_summary: str = Field(default="",max_length=3500)
    findings: str = Field(default="",max_length=9000)
    review_steps: list[str] = Field(default_factory=list,max_length=6)
    question: str = Field(default="",max_length=500)
    confirm: bool = False

@router.get("/assistant-workspace")
def assistant_workspace(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Cheap permission-filtered workload snapshot, no model requests."""
    p=profile(db,user)
    _require(p)
    visible=[c for c in _authorized_cases_query(db,p,user.id)
        .order_by(CaseAssignment.updated_at.desc(),CaseAssignment.id.desc()).limit(300).all()
        if _visible(c,p,user.id)]
    active=[c for c in visible if c.status!="CLOSED"]
    mine=[c for c in active if c.assignee_id==user.id]
    ids=[c.id for c in visible]
    latest=_current_report_ids(db,ids) if has(p,"human_validation") else {}
    pending=[r for r in latest.values()
             if r.status=="SUBMITTED" and r.created_by!=user.id]
    return {
        "can_create":has(p,"add_intelligence"),
        "my_assignments":len(mine),
        "visible_open_cases":len(active),
        "reports_for_my_review":len(pending),
        "recent_cases":[{"id":c.id,"title":c.title[:120],"status":c.status,
            "department":c.target_department,"province":c.target_province,
            "assigned_to_me":c.assignee_id==user.id} for c in active[:5]],
        "paid_provider_called":False
    }

@router.post("/assistant-handoff")
def assistant_handoff(body: AssistantHandoff,
                      user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    """Turn one permission-checked source and existing analysis into draft work.

    Does not invoke AI or send a task automatically. Requires explicit client
    confirmation, officer authorization, and source/jurisdiction revalidation.
    """
    from .models import AuditEvent
    p=profile(db,user)
    _require(p,"add_intelligence")
    if body.confirm is not True:
        raise HTTPException(422,"Officer confirmation is required")
    if body.department not in DEPARTMENTS:
        raise HTTPException(422,"Choose an authorized department")
    source=_source(db,p,body.source_type.upper(),body.source_id,body.campaign_id)
    destination=_validate_route(source,p,body.target_scope,body.target_province)
    assignee=_assignee(db,body.target_scope,destination,body.assignee_id)
    existing=(db.query(CaseAssignment)
        .filter(CaseAssignment.created_by==user.id,
                CaseAssignment.source_type==source["source_type"],
                CaseAssignment.source_id==source["source_id"],
                CaseAssignment.campaign_id==source["campaign_id"],
                CaseAssignment.status!="CLOSED")
        .order_by(CaseAssignment.id.desc()).first())
    if existing:
        return {"case":_case_view(existing),"existing":True,
                "report_id":None,"paid_provider_called":False}
    origin_scope,origin_province=_team(p)
    title=_clean(body.title,240) or source["title"] or "Intelligence review"
    validated_steps=[step.strip()[:1200] for step in body.review_steps
                     if isinstance(step,str) and step.strip()][:5]
    # The agent's text is an officer-editable suggestion, never an established
    # fact. The originating source is independently rechecked above.
    summary=(body.executive_summary.strip() or
        "Tinjau rekaman sumber terkait untuk memutuskan apakah pemeriksaan diperlukan.")[:3500]
    findings=(body.findings.strip() or source["excerpt"])[:9000]
    limits=("Draf disiapkan dari analisis asisten dan sumber yang terlampir. "
            "Kesimpulan, kutipan terhadap sumber lain, lokasi, pelanggaran dan "
            "status hukum belum dinyatakan terverifikasi. Petugas harus "
            "memeriksa dokumen primer, tanggal, dan kecocokan konteks.")
    item=CaseAssignment(
        title=title,source_type=source["source_type"],source_id=source["source_id"],
        campaign_id=source["campaign_id"],source_url=source["source_url"],
        source_excerpt=source["excerpt"],
        tags_json=json.dumps(source["tags"],ensure_ascii=False),
        suggested_provinces_json=json.dumps(source["suggested_provinces"],ensure_ascii=False),
        verified_province=source["verified_province"] or "",
        originating_scope=origin_scope,originating_province=origin_province,
        target_scope=body.target_scope,target_province=destination,
        target_department=body.department,assignee_id=assignee,
        created_by=user.id,status="ASSIGNED" if assignee else "OPEN",
        notes=("Handoff dari AI Assistant. Petugas meninjau sumber sebelum tindak lanjut."))
    db.add(item)
    db.flush()
    snapshot={"case_id":item.id,"source_type":source["source_type"],
              "source_id":source["source_id"],"campaign_id":source["campaign_id"],
              "source_url":source["source_url"],"source_excerpt":source["excerpt"],
              "source_tags":source["tags"],"verified_province":source["verified_province"],
              "original_question":body.question,
              "origin":"ASSISTANT_DRAFT_OFFICER_CONFIRMATION",
              "other_claims_require_independent_review":True,
              "created_at":datetime.now(timezone.utc).isoformat()}
    report=CaseReport(
        case_id=item.id,title=("Draf kajian: "+title)[:240],
        executive_summary=summary,
        findings=findings,
        verification_notes=limits,
        recommendations="\n\n".join(f"{i}. {step}" for i,step in enumerate(validated_steps,1)) or
                        "Verifikasi sumber asli dan kewenangan unit penerima.",
        source_snapshot_json=json.dumps(snapshot,ensure_ascii=False),
        status="DRAFT",created_by=user.id)
    db.add(report)
    db.flush()
    db.add(CaseTransition(case_id=item.id,actor_id=user.id,
        action="ASSISTANT_HANDOFF",details_json=json.dumps({
            "report_id":report.id,"department":body.department,"target_scope":body.target_scope,
            "target_province":destination,"assignee_id":assignee,
            "ai_text_is_unverified":True},ensure_ascii=False)))
    db.add(AuditEvent(subject_type="CaseAssignment",subject_id=str(item.id),
        action="ASSISTANT_HANDOFF",actor_id=str(user.id),actor_name=p.get("name",""),
        changes_json=json.dumps({"report_id":report.id,"department":body.department,
            "source_id":source["source_id"],"human_confirmation":True},ensure_ascii=False),
        occurred_at=datetime.now(timezone.utc).isoformat()))
    db.commit()
    return {"case":_case_view(item),"report_id":report.id,
            "existing":False,"paid_provider_called":False,
            "review_required":True}
