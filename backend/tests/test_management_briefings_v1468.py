"""v146.8 report aggregation, jurisdiction and CSV security acceptance."""
import csv
import io
from datetime import datetime, timedelta
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import User, AccessGrant
from app.access import default_permissions, profile
from app.casework import CaseAssignment, CaseReport, CaseTransition
from app.management_reporting import build_briefing, briefing_csv, scoped_cases, _safe_csv_cell


def dataset():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    for uid, role, scope, province in [
        (1, "National Administrator", "Nationwide", ""),
        (2, "Provincial Analyst", "Province", "Riau"),
        (3, "Provincial Analyst", "Province", "Bali"),
        (4, "Viewer", "Province", "Riau"),
    ]:
        db.add(User(id=uid, email=str(uid)+"@example.invalid",
                    full_name="Officer "+str(uid), password_hash="unused"))
        db.add(AccessGrant(user_id=uid, access_role=role,
            geographic_scope=scope, province=province, status="Active",
            permissions_json=json.dumps(default_permissions(role))))
    now = datetime.utcnow()
    common = dict(source_type="SOCIAL", source_id="15", campaign_id=10,
                  source_url="https://example.invalid/post/15",
                  originating_scope="NATIONAL", originating_province="",
                  target_department="Penanganan Pelanggaran", created_by=1,
                  created_at=now-timedelta(hours=3), updated_at=now)
    db.add(CaseAssignment(id=1,title="Riau alleged election incident",status="OPEN",
        target_scope="PROVINCE",target_province="Riau",verified_province="Riau",**common))
    db.add(CaseAssignment(id=2,title="Riau second assignment",status="CLOSED",
        target_scope="PROVINCE",target_province="Riau",verified_province="Riau",**common))
    db.add(CaseAssignment(id=3,title="Bali issue",status="IN_REVIEW",
        target_scope="PROVINCE",target_province="Bali",verified_province="Bali",
        **dict(common,source_id="18",campaign_id=11)))
    db.add(CaseAssignment(id=4,title="Older case",status="OPEN",
        target_scope="NATIONAL",target_province="",verified_province="",
        **dict(common,created_at=now-timedelta(days=40))))
    db.add(CaseReport(id=8,case_id=1,title="Review note",status="APPROVED",
                      created_by=1,created_at=now,updated_at=now))
    db.add(CaseTransition(case_id=1,actor_id=1,action="ASSIGNED",
                          happened_at=now-timedelta(hours=1)))
    db.commit()
    return db


def test_national_counts_deduplicate_sources():
    db=dataset()
    try:
        summary=build_briefing(db,profile(db,db.get(User,1)),1)
        assert summary["metrics"]["assignments"]==3
        assert summary["metrics"]["unique_linked_sources"]==2
        assert summary["metrics"]["active_assignments"]==2
        assert summary["metrics"]["closed_assignments"]==1
        assert summary["metrics"]["approved_reports"]==1
        assert summary["metrics"]["officer_transitions_in_window"]==1
        assert summary["counts_complete_for_window"] is True
        assert summary["paid_provider_called"] is False
        assert summary["generated_by_ai"] is False
    finally: db.close()


def test_province_scope_applied_before_metrics_and_topic_filter():
    db=dataset()
    try:
        p=profile(db,db.get(User,2))
        assert build_briefing(db,p,2)["metrics"]["assignments"]==2
        assert build_briefing(db,p,2)["metrics"]["unique_linked_sources"]==1
        assert build_briefing(db,p,2,topic="Bali")["metrics"]["assignments"]==0
        assert build_briefing(db,profile(db,db.get(User,3)),3)["metrics"]["assignments"]==1
        assert build_briefing(db,profile(db,db.get(User,4)),4)["metrics"]["assignments"]==2
    finally: db.close()


def test_csv_scoped_and_formula_safe():
    db=dataset()
    try:
        result=briefing_csv("weekly","",db.get(User,2),db)
        rows=list(csv.DictReader(io.StringIO(result.body.decode("utf-8-sig"))))
        assert len(rows)==2
        assert all("Riau" in row["Case title"] for row in rows)
        assert _safe_csv_cell("=HYPERLINK(1)")=="'=HYPERLINK(1)"
        assert result.headers["cache-control"]=="no-store"
    finally: db.close()


def test_bad_period_or_topic_rejected():
    db=dataset()
    try:
        p=profile(db,db.get(User,1))
        with pytest.raises(HTTPException) as exc:
            scoped_cases(db,p,1,"all")
        assert exc.value.status_code==422
        with pytest.raises(HTTPException):
            scoped_cases(db,p,1,"weekly","a"*121)
    finally: db.close()
