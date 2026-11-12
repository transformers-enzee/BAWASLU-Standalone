"""Permission-scoped management reports from existing officer casework.

Counts are assignments created in a rolling UTC window, not social post
counts or legally established electoral violations. No paid AI calls.
"""
from collections import Counter
from typing import Literal
from datetime import datetime, timedelta, timezone
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .models import User
from .access import profile
from .casework import CaseAssignment, CaseReport, CaseTransition, _require, _visible
from .management_report_templates import build_interim_template, render_pdf, render_docx, render_xlsx

router = APIRouter(prefix="/api/management-reporting", tags=["management-reporting"])
PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}
DISCLAIMER = (
    "Counts cover authorized officer casework assignments created in this UTC period, "
    "not all monitored social posts or confirmed electoral-law violations. "
    "Closed assignments and approved reports are workflow states, not legal outcomes."
)


def scoped_cases(db: Session, access: dict, user_id: int, period: str, topic: str = "", now=None):
    if period not in PERIOD_DAYS:
        raise HTTPException(422, "Period must be daily, weekly or monthly")
    topic = " ".join(str(topic or "").split())
    if len(topic) > 120:
        raise HTTPException(422, "Topic filter is too long")
    _require(access)
    end = now or datetime.utcnow()
    start = end - timedelta(days=PERIOD_DAYS[period])
    # Narrow SQL at the database first, not after fetching every province's cases.
    # This predicate mirrors casework._visible; retain that guard as defense in depth.
    query = db.query(CaseAssignment).filter(
        CaseAssignment.created_at >= start, CaseAssignment.created_at <= end)
    geographic_scope = access.get("geographic_scope")
    province = access.get("province") or ""
    if geographic_scope == "Province":
        if not province:
            return [], start, end, topic
        query = query.filter(or_(
            and_(CaseAssignment.originating_scope == "PROVINCE",
                 CaseAssignment.originating_province == province),
            and_(CaseAssignment.target_scope == "PROVINCE",
                 CaseAssignment.target_province == province,
                 CaseAssignment.verified_province == province)))
    elif geographic_scope != "Nationwide":
        query = query.filter(or_(
            CaseAssignment.created_by == user_id,
            and_(CaseAssignment.assignee_id == user_id,
                 CaseAssignment.verified_province == province)))
    candidates = query.order_by(
        CaseAssignment.created_at.desc(), CaseAssignment.id.desc()).all()
    authorized = [row for row in candidates if _visible(row, access, user_id)]
    if topic:
        needle = topic.casefold()
        authorized = [row for row in authorized if needle in " ".join([
            row.title or "", row.source_excerpt or "", row.target_department or ""
        ]).casefold()]
    return authorized, start, end, topic


def _utc_publication_time(raw):
    """Only explicit UTC/offset publication timestamps qualify for rolling windows.

    Date-only and timezone-naive strings cannot safely be assigned to the
    selected UTC period and are counted as missing timestamp coverage.
    """
    value = str(raw or "").strip()[:64]
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if timestamp.tzinfo is None:
        return None
    return timestamp.astimezone(timezone.utc).replace(tzinfo=None)


def monitoring_snapshot_from_findings(findings, start, end, topic=""):
    """Pure, deduplicated and sample-limited view over AUTHORIZED Inbox findings.

    Period means original post publication time (not capture time).
    No claims about total social conversation volume are made.
    """
    seen=set()
    sentiments=Counter()
    platforms=Counter()
    unique_relevant=0
    period_posts=0
    unknown_dates=0
    outside_window=0
    flagged=0
    concerns=0
    narratives=0
    topic_needle=str(topic or "").casefold().strip()
    for finding in findings or []:
        kind=str(finding.get("kind") or "")
        for post in finding.get("posts") or []:
            if not isinstance(post,dict):
                continue
            sid=str(post.get("canonical_source_id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            if topic_needle and topic_needle not in " ".join([
                str(post.get("message_original") or ""),
                str(finding.get("title") or "")
            ]).casefold():
                continue
            unique_relevant+=1
            published=_utc_publication_time(post.get("published_at_raw"))
            if published is None:
                unknown_dates+=1
                continue
            if not (start<=published<=end):
                outside_window+=1
                continue
            period_posts+=1
            sentiment=str(post.get("sentiment") or "UNCLASSIFIED").upper()
            sentiments[sentiment if sentiment in ("POSITIVE","NEGATIVE","NEUTRAL")
                       else "UNCLASSIFIED"]+=1
            platforms[str(post.get("platform") or "Unknown")]+=1
            if kind=="source_review":
                flagged+=1
            if kind=="discussion" or "concerns" in (finding.get("players") or []):
                concerns+=1
            if kind=="narrative_candidate" and "narratives" in (finding.get("players") or []):
                narratives+=1
    assert period_posts==sum(sentiments.values())==sum(platforms.values())
    return {
        "enabled":True,
        "published_in_period":period_posts,
        "unique_relevant_sources_in_recent_inbox":unique_relevant,
        "publication_date_unknown":unknown_dates,
        "published_outside_period":outside_window,
        "flagged_potential_violation_posts":flagged,
        "public_concern_posts":concerns,
        "emerging_narrative_posts":narratives,
        "sentiment_counts":dict(sentiments),
        "platform_counts":dict(platforms),
        "publication_time_basis":"EXPLICIT_UTC_OR_OFFSET_SOURCE_PUBLISHED_AT",
        "period_semantics":"SOURCE_PUBLICATION_WINDOW_NOT_CAPTURE_WINDOW",
        "inbox_window_limit":300,
        "inbox_window_unit":"LINKS_PER_AUTHORIZED_CAMPAIGN",
        "inbox_truncation_status":"UNKNOWN",
        "all_platform_conversations_counted":False,
        "legal_violations_confirmed":False,
        "source_basis":"PERMISSION_SCOPED_SAVED_INTELLIGENCE_INBOX",
        "derived_from_officer_casework":False,
        "paid_provider_called":False,
        "disclaimer":"Counts are deduplicated saved relevant posts with explicit publication timestamps from a bounded authorized Inbox window. They are not all captured posts, total online conversations, unique people, verified incidents, or confirmed violations.",
    }


def build_briefing(db: Session, access: dict, user_id: int,
                   period: str = "weekly", topic: str = "", now=None, language="id",
                   include_monitoring=False):
    cases, start, end, topic = scoped_cases(db, access, user_id, period, topic, now)
    ids = [item.id for item in cases]
    reports = (db.query(CaseReport).filter(CaseReport.case_id.in_(ids)).all()
               if ids else [])
    transitions = (db.query(CaseTransition)
        .filter(CaseTransition.case_id.in_(ids),
                CaseTransition.happened_at >= start,
                CaseTransition.happened_at <= end).all() if ids else [])
    statuses = Counter(row.status for row in cases)
    # Report versions are an audit trail. Operational KPIs reflect ONLY the
    # most recent version for each assignment, not every historical report.
    latest_by_case = {}
    for report in sorted(reports, key=lambda row: (row.created_at, row.id)):
        latest_by_case[report.case_id] = report
    latest_reports = {case_id: report.status for case_id, report in latest_by_case.items()}
    report_counts = Counter(latest_reports.values())
    departments = Counter(row.target_department for row in cases)
    provinces = Counter(row.verified_province or "Unverified" for row in cases)
    source_keys = {(row.source_type, row.source_id,
                    row.campaign_id if row.source_type == "SOCIAL" else None)
                   for row in cases}
    snapshot = {
        "period": period,
        "topic_filter": topic,
        "window_start_utc": start.isoformat() + "Z",
        "window_end_utc": end.isoformat() + "Z",
        "scope": {"geographic_scope": access.get("geographic_scope"),
                  "province": access.get("province") or ""},
        "metrics": {
            "assignments": len(cases),
            "unique_linked_sources": len(source_keys),
            "active_assignments": sum(row.status != "CLOSED" for row in cases),
            "closed_assignments": statuses["CLOSED"],
            "submitted_reports": report_counts["SUBMITTED"],
            "approved_reports": report_counts["APPROVED"],
            "assignments_with_reports": len(latest_by_case),
            "assignments_without_reports": len(cases) - len(latest_by_case),
            "report_versions_recorded": len(reports),
            "officer_transitions_in_window": len(transitions),
        },
        "case_status_counts": dict(statuses),
        "report_status_counts": dict(report_counts),
        "report_status_basis": "LATEST_REPORT_PER_AUTHORIZED_ASSIGNMENT",
        "report_coverage": {
            "assignments_in_period": len(cases),
            "assignments_with_reports": len(latest_by_case),
            "assignments_without_reports": len(cases) - len(latest_by_case),
            "stored_report_versions": len(reports),
            "preview_limit": 12,
            "preview_rows": min(len(cases), 12),
            "template_limit": 8,
            "template_rows": min(len(cases), 8),
            "preview_is_sample": len(cases) > 12,
            "template_is_sample": len(cases) > 8,
        },
        "department_counts": dict(departments),
        "verified_incident_province_counts": dict(provinces),
        "recent_cases": [
            {"id": row.id, "title": row.title, "status": row.status,
             "department": row.target_department, "source_type": row.source_type,
             "source_id": row.source_id, "campaign_id": row.campaign_id,
             "source_url": row.source_url, "verified_province": row.verified_province,
             "created_at": row.created_at.isoformat(),
             "latest_report_status": latest_reports.get(row.id),
             "evidence_excerpt": (row.source_excerpt or "")[:320]}
            for row in cases[:12]
        ],
        "disclaimer": DISCLAIMER,
        "data_basis": "AUTHORIZED_OFFICER_CASEWORK",
        "counts_complete_for_window": True,
        "query_scope": "SQL_AND_CASEWORK_VISIBILITY",
        "generated_by_ai": False,
        "paid_provider_called": False,
    }
    if include_monitoring:
        snapshot["data_basis"] = "AUTHORIZED_OFFICER_CASEWORK_AND_SAVED_INBOX_MONITORING_SAMPLE"
        snapshot["disclaimer"] = (
            DISCLAIMER + " Optional monitoring counts are separately sampled "
            "from the permission-scoped, relevant, saved Inbox feed, using "
            "explicit publication timestamps only; they are not totals.")
        # Shared permission-scoped Inbox cache. No extra raw-post query or model call.
        from .inbox_radar import live_inbox_findings
        findings, _ = live_inbox_findings(db, access)
        snapshot["monitoring"] = monitoring_snapshot_from_findings(
            findings, start, end, topic)
    else:
        snapshot["monitoring"] = {"enabled":False,
                                  "reason":"NOT_REQUESTED_TO_KEEP_REPORT_FAST"}
    snapshot["template"] = build_interim_template(snapshot, language)
    return snapshot


@router.get("/briefing")
def briefing(period: str = "weekly", topic: str = "", language: Literal["id","en"] = "id",
             user: User = Depends(current_user), db: Session = Depends(get_db),
             include_monitoring: bool = False):
    return build_briefing(db, profile(db, user), user.id, period, topic,
                          language=language, include_monitoring=include_monitoring)


def _safe_csv_cell(value):
    value = str(value if value is not None else "")
    return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


@router.get("/briefing.csv")
def briefing_csv(period: str = "weekly", topic: str = "",
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    cases, _, _, _ = scoped_cases(db, profile(db, user), user.id, period, topic)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Case ID", "Created UTC", "Status", "Department",
                     "Verified incident province", "Source type", "Source ID",
                     "Campaign ID", "Source URL", "Case title"])
    for row in cases:
        writer.writerow([_safe_csv_cell(v) for v in (
            row.id, row.created_at.isoformat(), row.status, row.target_department,
            row.verified_province, row.source_type, row.source_id,
            row.campaign_id, row.source_url, row.title)])
    return Response(content="\ufeff" + buffer.getvalue(),
                    media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="bawaslu-casework-briefing.csv"',
                             "Cache-Control": "private, no-store",
                             "X-Report-Source": "AUTHORIZED_OFFICER_CASEWORK"})


def _export_report(kind: str, period: str, topic: str, language: str, user: User,
                   db: Session, include_monitoring=False):
    """Rebuild only the officer-authorized casework snapshot for this export."""
    snapshot = build_briefing(db, profile(db, user), user.id, period, topic,
                              language=language, include_monitoring=include_monitoring)
    template = snapshot["template"]
    generators = {
        "pdf": (render_pdf, "application/pdf"),
        "docx": (render_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "xlsx": (render_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    }
    generator, media_type = generators[kind]
    content = generator(template)
    filename = "bawaslu-interim-briefing-" + period + "." + kind
    return Response(
        content=content, media_type=media_type,
        headers={"Cache-Control": "private, no-store",
                 "X-Report-Template": template["template_version"],
                 "X-Report-Approval": "DRAFT_NOT_APPROVED",
                 "X-Report-Monitoring": "SAMPLED_INBOX" if include_monitoring else "CASEWORK_ONLY",
                 "Content-Disposition": 'attachment; filename="' + filename + '"'})


@router.get("/briefing.pdf")
def briefing_pdf(period: str = "weekly", topic: str = "", language: Literal["id","en"] = "id",
                 user: User = Depends(current_user), db: Session = Depends(get_db),
                  include_monitoring: bool = False):
    return _export_report("pdf", period, topic, language, user, db,
                          include_monitoring=include_monitoring)


@router.get("/briefing.docx")
def briefing_docx(period: str = "weekly", topic: str = "", language: Literal["id","en"] = "id",
                  user: User = Depends(current_user), db: Session = Depends(get_db),
                  include_monitoring: bool = False):
    return _export_report("docx", period, topic, language, user, db,
                          include_monitoring=include_monitoring)


@router.get("/briefing.xlsx")
def briefing_xlsx(period: str = "weekly", topic: str = "", language: Literal["id","en"] = "id",
                  user: User = Depends(current_user), db: Session = Depends(get_db),
                  include_monitoring: bool = False):
    return _export_report("xlsx", period, topic, language, user, db,
                          include_monitoring=include_monitoring)
