"""Permission-scoped management reports from existing officer casework.

Counts are assignments created in a rolling UTC window, not social post
counts or legally established electoral violations. No paid AI calls.
"""
from collections import Counter
from datetime import datetime, timedelta
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from .auth import current_user
from .db import get_db
from .models import User
from .access import profile
from .casework import CaseAssignment, CaseReport, CaseTransition, _require, _visible

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
    candidates = (db.query(CaseAssignment)
        .filter(CaseAssignment.created_at >= start, CaseAssignment.created_at <= end)
        .order_by(CaseAssignment.created_at.desc(), CaseAssignment.id.desc()).all())
    # Apply the Action Desk's visibility model before aggregating or filtering.
    authorized = [row for row in candidates if _visible(row, access, user_id)]
    if topic:
        needle = topic.casefold()
        authorized = [row for row in authorized if needle in " ".join([
            row.title or "", row.source_excerpt or "", row.target_department or ""
        ]).casefold()]
    return authorized, start, end, topic


def build_briefing(db: Session, access: dict, user_id: int,
                   period: str = "weekly", topic: str = "", now=None):
    cases, start, end, topic = scoped_cases(db, access, user_id, period, topic, now)
    ids = [item.id for item in cases]
    reports = (db.query(CaseReport).filter(CaseReport.case_id.in_(ids)).all()
               if ids else [])
    transitions = (db.query(CaseTransition)
        .filter(CaseTransition.case_id.in_(ids),
                CaseTransition.happened_at >= start,
                CaseTransition.happened_at <= end).all() if ids else [])
    statuses = Counter(row.status for row in cases)
    report_counts = Counter(row.status for row in reports)
    departments = Counter(row.target_department for row in cases)
    provinces = Counter(row.verified_province or "Unverified" for row in cases)
    source_keys = {(row.source_type, row.source_id,
                    row.campaign_id if row.source_type == "SOCIAL" else None)
                   for row in cases}
    latest_reports = {}
    for report in sorted(reports, key=lambda item: (item.created_at, item.id)):
        latest_reports[report.case_id] = report.status
    return {
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
            "officer_transitions_in_window": len(transitions),
        },
        "case_status_counts": dict(statuses),
        "report_status_counts": dict(report_counts),
        "department_counts": dict(departments),
        "verified_incident_province_counts": dict(provinces),
        "recent_cases": [
            {"id": row.id, "title": row.title, "status": row.status,
             "department": row.target_department, "source_type": row.source_type,
             "source_id": row.source_id, "campaign_id": row.campaign_id,
             "source_url": row.source_url, "verified_province": row.verified_province,
             "created_at": row.created_at.isoformat(),
             "latest_report_status": latest_reports.get(row.id)}
            for row in cases[:12]
        ],
        "disclaimer": DISCLAIMER,
        "data_basis": "AUTHORIZED_OFFICER_CASEWORK",
        "counts_complete_for_window": True,
        "generated_by_ai": False,
        "paid_provider_called": False,
    }


@router.get("/briefing")
def briefing(period: str = "weekly", topic: str = "",
             user: User = Depends(current_user), db: Session = Depends(get_db)):
    return build_briefing(db, profile(db, user), user.id, period, topic)


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
                             "Cache-Control": "no-store"})
