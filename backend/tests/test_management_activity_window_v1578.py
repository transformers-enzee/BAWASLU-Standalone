"""v157.8 Activity CSV avoids unnecessary case-creation read and declares time bounds."""
from datetime import datetime,timedelta
import csv,io
import pytest
from fastapi import HTTPException
from app.models import User
from app.access import profile
from app.casework import CaseAssignment,CaseTransition
import app.management_reporting as mr
from test_management_briefings_v1468 import dataset

def activity(db,uid=1,period="weekly",topic=""):
    return mr.briefing_activity_csv(period,topic,db.get(User,uid),db)

def rows(response):
    return list(csv.DictReader(io.StringIO(response.body.decode("utf-8-sig"))))

def test_period_window_matches_existing_casework_window():
    db=dataset()
    try:
        now=datetime(2026,11,16,4,30,0)
        access=profile(db,db.get(User,1))
        _,start,end,topic=mr.scoped_cases(db,access,1,"weekly","  example  text ",now)
        a,b,c=mr._activity_period_window(access,"weekly","  example  text ",now)
        assert (a,b,c)==(start,end,topic)
    finally:db.close()

def test_activity_csv_does_not_load_creation_cohort(monkeypatch):
    db=dataset()
    try:
        def unexpected(*args,**kwargs):
            raise AssertionError("scoped_cases should not run for Activity CSV")
        monkeypatch.setattr(mr,"scoped_cases",unexpected)
        db.add(CaseTransition(case_id=1,actor_id=1,
            action="REPORT_APPROVED",happened_at=datetime.utcnow()-timedelta(seconds=5)))
        db.commit()
        result=activity(db)
        assert len(rows(result))==1
        assert rows(result)[0]["Current approval reconciliation"]=="STILL_APPROVED"
    finally:db.close()

def test_activity_csv_reports_exact_window_and_status_observation_time():
    db=dataset()
    try:
        db.add(CaseTransition(case_id=1,actor_id=1,
            action="REPORT_SUBMITTED",happened_at=datetime.utcnow()-timedelta(seconds=5)))
        db.commit()
        response=activity(db)
        item=rows(response)[0]
        assert item["Audit window start UTC"]==response.headers["X-Report-Window-Start-UTC"]
        assert item["Audit window end UTC"]==response.headers["X-Report-Window-End-UTC"]
        assert item["Latest report status observed UTC"]==item["Audit window end UTC"]
        assert datetime.fromisoformat(item["Audit window end UTC"].rstrip("Z"))-datetime.fromisoformat(
            item["Audit window start UTC"].rstrip("Z"))==timedelta(days=7)
        assert item["Current approval reconciliation"]=="NOT_APPLICABLE_NO_APPROVAL_EVENT"
    finally:db.close()

@pytest.mark.parametrize("period,topic",[
    ("yearly",""),("weekly","x"*121)])
def test_activity_csv_invalid_period_or_oversized_topic_rejected(period,topic):
    db=dataset()
    try:
        with pytest.raises(HTTPException) as err:activity(db,period=period,topic=topic)
        assert err.value.status_code==422
    finally:db.close()

def test_province_scoping_still_excludes_foreign_cases():
    db=dataset()
    try:
        now=datetime.utcnow()-timedelta(seconds=5)
        db.add_all([
            CaseTransition(case_id=1,actor_id=1,action="REPORT_APPROVED",happened_at=now),
            CaseTransition(case_id=3,actor_id=1,action="REPORT_APPROVED",happened_at=now)
        ])
        db.commit()
        report=activity(db,uid=2)
        assert {x["Case ID"] for x in rows(report)}=={"1"}
        assert report.headers["Cache-Control"]=="private, no-store"
    finally:db.close()
