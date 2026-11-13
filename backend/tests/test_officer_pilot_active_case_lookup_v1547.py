"""v154.7: complete active-case detection for an authorized pilot shortlist.

Tests use isolated in-memory SQLite. SQL limits and partitioning are also
checked with PostgreSQL dialect compilation. No live casework is written.
"""
from types import SimpleNamespace as Obj
from unittest.mock import patch
import pytest
from sqlalchemy import event
from sqlalchemy.dialects import postgresql

from app.access import profile
from app.casework import (
    CaseAssignment,CaseTransition,_pilot_visible_active_cases,pilot_intake
)
from app.models import User
from app.officer_pilot_intake import officer_pilot_candidates,_positive_id
from test_casework_workflow import dataset
from test_officer_pilot_intake_v1544 import post,finding,_patch


def _case(sid, campaign=90, owner=1, scope="NATIONAL", province="",status="OPEN"):
    return CaseAssignment(
        title="QA case",source_type="SOCIAL",source_id=str(sid),
        campaign_id=campaign,originating_scope=scope,
        originating_province=province,target_scope=scope,
        target_province=province,verified_province=province,
        target_department="Pengawasan",created_by=owner,status=status)


def _rows(*pairs):
    return [{"source_id":str(sid),"campaign_id":str(cid)} for sid,cid in pairs]


def test_empty_source_pairs_avoid_database_queries():
    db=dataset()
    queries=[]
    def record(conn,cursor,statement,params,ctx,many):queries.append(statement)
    event.listen(db.get_bind(),"before_cursor_execute",record)
    try:
        assert _pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,[])==[]
        assert queries==[]
    finally:
        event.remove(db.get_bind(),"before_cursor_execute",record)
        db.close()


def test_many_existing_cases_for_one_source_do_not_hide_second_source():
    db=dataset()
    try:
        db.add_all([_case(11) for _ in range(260)]+[_case(12)])
        db.commit()
        cases=_pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,
            _rows((11,90),(12,90)))
        assert len(cases)==2
        assert {c.source_id for c in cases}=={"11","12"}
        assert next(c for c in cases if c.source_id=="11").id==260
        assert next(c for c in cases if c.source_id=="12").id==261
    finally: db.close()


def test_returns_latest_active_record_not_latest_closed_record():
    db=dataset()
    try:
        early=_case(11);db.add(early);db.flush()
        db.add(_case(11,status="CLOSED"));db.commit()
        found=_pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,_rows((11,90)))
        assert [c.id for c in found]==[early.id]
    finally:db.close()


def test_exact_campaign_pair_prevents_other_campaign_case_reuse():
    db=dataset()
    try:
        db.add_all([_case(11,90),_case(11,91)])
        db.commit()
        rows=_pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,_rows((11,90)))
        assert len(rows)==1 and rows[0].campaign_id==90
    finally:db.close()


def test_multiple_campaigns_are_partitioned_independently():
    db=dataset()
    try:
        db.add_all([_case(11,90),_case(11,90),_case(11,91)])
        db.commit()
        rows=_pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,
            _rows((11,90),(11,91)))
        assert {case.campaign_id for case in rows}=={90,91}
        assert len(rows)==2
        assert max(c.id for c in rows if c.campaign_id==90)==2
    finally:db.close()


def test_province_query_does_not_reveal_hidden_national_cases():
    db=dataset()
    try:
        db.add_all([_case(11,owner=1,scope="NATIONAL"),
                    _case(11,owner=2,scope="PROVINCE",province="Riau")])
        db.commit()
        visible=_pilot_visible_active_cases(db,profile(db,db.get(User,2)),2,_rows((11,90)))
        assert len(visible)==1
        assert visible[0].originating_province=="Riau"
        assert visible[0].created_by==2
    finally:db.close()


def test_unrelated_province_sees_no_active_cases():
    db=dataset()
    try:
        db.add(_case(11,owner=2,scope="PROVINCE",province="Riau"))
        db.commit()
        assert _pilot_visible_active_cases(db,profile(db,db.get(User,3)),3,
            _rows((11,90)))==[]
    finally:db.close()


def test_closed_only_cases_do_not_appear_active():
    db=dataset()
    try:
        db.add(_case(11,status="CLOSED"))
        db.commit()
        assert _pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,
            _rows((11,90)))==[]
    finally:db.close()


def test_previously_hidden_active_case_does_not_override_allowed_case():
    db=dataset()
    try:
        db.add_all([_case(11,owner=2,scope="PROVINCE",province="Riau"),
                    _case(11,owner=3,scope="PROVINCE",province="Bali")])
        db.commit()
        visible=_pilot_visible_active_cases(db,profile(db,db.get(User,2)),2,
            _rows((11,90)))
        assert len(visible)==1 and visible[0].originating_province=="Riau"
    finally:db.close()


def test_latest_active_per_pair_is_bounded_to_twelve_in_sql():
    db=dataset()
    try:
        pairs=_rows(*[(i,90) for i in range(1,26)])
        db.add_all([_case(i) for i in range(1,26)])
        db.commit()
        queries=[]
        def capture(conn,cursor,sql,params,context,many):
            if "ROW_NUMBER" in sql.upper():queries.append(sql)
        event.listen(db.get_bind(),"before_cursor_execute",capture)
        try:
            result=_pilot_visible_active_cases(db,profile(db,db.get(User,1)),1,pairs)
        finally:event.remove(db.get_bind(),"before_cursor_execute",capture)
        assert len(result)==12
        assert len(queries)==1
        assert "row_number()" in queries[0].lower()
        assert "case_assignments" in queries[0]
    finally:db.close()


@pytest.mark.parametrize("value",[
    "9"*5000,"0"*6000,str(2**63),"-1","١٢","123 OR 1=1",
    "",None,False,True,"1.0","0"
])
def test_malicious_or_oversized_source_ids_are_rejected(value):
    assert _positive_id(value)==""


def test_safe_64bit_int_and_leading_zero_ids_are_normalized():
    assert _positive_id("0000000001")=="1"
    assert _positive_id(str(2**63-1))==str(2**63-1)


def test_invalid_large_ids_never_create_inbox_casework_links():
    result=officer_pilot_candidates([finding(posts=[post(source="9"*5000)])])
    assert result["items"]==[]
    assert result["observed_authorized_unique_sources"]==0


def test_cached_saved_inbox_pilot_reuses_case_even_after_more_than_250_active_records(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding(posts=[post(11,90),post(12,90)])])
        db.add_all([_case(11) for _ in range(260)]+[_case(12)])
        db.commit()
        result=pilot_intake(db.get(User,1),db)
        assert result["visible_case_lookup_arbitrary_case_cap_removed"] is True
        assert result["visible_case_lookup_pairs_limit"]==12
        assert result["observed_authorized_unique_sources"]==2
        for row in result["items"]:
            assert row["case_already_exists_in_visible_scope"] is True
            assert row["casework_link"].endswith("&tab=reports")
        assert {row["visible_open_case_id"] for row in result["items"]}=={260,261}
        assert db.query(CaseAssignment).count()==261
        assert db.query(CaseTransition).count()==0
    finally:db.close()


def test_pilot_lookup_is_read_only_even_with_existing_case(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding()])
        db.add(_case(11));db.commit()
        writes=[]
        def collect(conn,cursor,sql,params,ctx,many):
            if sql.lstrip().lower().startswith(("insert ","update ","delete ")):
                writes.append(sql)
        event.listen(db.get_bind(),"before_cursor_execute",collect)
        try:result=pilot_intake(db.get(User,1),db)
        finally:event.remove(db.get_bind(),"before_cursor_execute",collect)
        assert writes==[]
        assert result["no_assignment_created"] is True
    finally:db.close()


def test_no_casework_bypass_through_mismatched_candidate_scope(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding()])
        db.add(_case(11,owner=3,scope="PROVINCE",province="Bali"))
        db.commit()
        result=pilot_intake(db.get(User,2),db)
        assert all(not row["case_already_exists_in_visible_scope"]
                   for row in result["items"])
    finally:db.close()
