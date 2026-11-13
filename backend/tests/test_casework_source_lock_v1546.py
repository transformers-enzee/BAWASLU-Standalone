"""v154.6: shared-source row locks and transparent case-routing reuse.

Row-lock SQL is compiled against PostgreSQL, while behavioral fixtures run
in isolated SQLite. No live officer cases or DB writes are performed.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql
from sqlalchemy import event
from unittest.mock import patch

from app.casework import (
    _assignment_source_lock_query,_lock_assignment_source, CaseAssignment,
    CaseTransition,create_case,NewCase
)
import app.casework as casework
from app.models import CampaignEvidence
from test_casework_workflow import dataset,confirmed
from test_officer_pilot_end_to_end_v1545 import request,user

SOCIAL={"source_type":"SOCIAL","source_id":"11","campaign_id":90}
INTELLIGENCE={"source_type":"INTELLIGENCE","source_id":"INT-2026-000001","campaign_id":None}

def test_social_source_lock_uses_postgres_select_for_update():
    db=dataset()
    try:
        sql=str(_assignment_source_lock_query(db,SOCIAL).statement.compile(
            dialect=postgresql.dialect()))
        assert "FOR UPDATE" in sql
        assert "campaign_evidence" in sql
        assert "campaign_evidence.campaign_id" in sql
        assert "campaign_evidence.result_id" in sql
        assert "users" not in sql.lower()
    finally:db.close()

def test_intelligence_source_lock_uses_its_shared_record_not_a_user_lock():
    db=dataset()
    try:
        sql=str(_assignment_source_lock_query(db,INTELLIGENCE).statement.compile(
            dialect=postgresql.dialect()))
        assert "FOR UPDATE" in sql
        assert "intelligence_items" in sql
        assert "intelligence_items.intelligence_id" in sql
        assert "users" not in sql.lower()
    finally:db.close()

def test_existing_saved_social_link_can_be_locked_without_mutation():
    db=dataset()
    try:
        assert _lock_assignment_source(db,SOCIAL) is None
        assert db.query(CaseAssignment).count()==0
    finally:db.close()

def test_missing_campaign_evidence_link_fails_closed():
    db=dataset()
    try:
        db.query(CampaignEvidence).filter_by(campaign_id=90,result_id=11).delete()
        db.commit()
        with pytest.raises(HTTPException) as exc:
            _lock_assignment_source(db,SOCIAL)
        assert exc.value.status_code==403
        assert db.query(CaseAssignment).count()==0
    finally:db.close()

def test_missing_intelligence_source_lock_fails_closed():
    db=dataset()
    try:
        with pytest.raises(HTTPException) as exc:
            _lock_assignment_source(db,INTELLIGENCE)
        assert exc.value.status_code==403
    finally:db.close()

def test_invalid_internal_source_type_does_not_bypass_lock():
    db=dataset()
    try:
        with pytest.raises(HTTPException) as exc:
            _assignment_source_lock_query(db,{"source_type":"UNKNOWN","source_id":"11"})
        assert exc.value.status_code==422
    finally:db.close()

def test_both_national_officers_share_the_exact_same_source_lock():
    db=dataset()
    try:
        observed=[]
        lock=casework._lock_assignment_source
        def capture(session,source):
            observed.append((source["source_type"],source["source_id"],source["campaign_id"]))
            return lock(session,source)
        with patch.object(casework,"_lock_assignment_source",side_effect=capture):
            first=request(db,ident=1)
            second=request(db,ident=4)
        assert observed==[("SOCIAL","11",90),("SOCIAL","11",90)]
        assert second["id"]==first["id"]
        assert second["existing"] is True
        assert second["assignment_created"] is False
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_repeated_request_exact_route_reports_a_match():
    db=dataset()
    try:
        first=request(db)
        second=request(db)
        assert first["requested_route_matches_existing"] is True
        assert first["route_change_requires_separate_audited_action"] is False
        assert second["requested_route_matches_existing"] is True
        assert second["route_change_requires_separate_audited_action"] is True
    finally:db.close()

def test_repeated_request_different_department_requires_audited_route():
    db=dataset()
    try:
        first=request(db,department="Pengawasan")
        second=request(db,department="Data & Analisis")
        assert second["id"]==first["id"]
        assert second["requested_route_matches_existing"] is False
        assert second["route_change_requires_separate_audited_action"] is True
        assert db.get(CaseAssignment,first["id"]).target_department=="Pengawasan"
        assert db.query(CaseAssignment).count()==1
    finally:db.close()

def test_repeated_request_new_assignee_never_silently_reassigns_officer():
    db=dataset()
    try:
        first=request(db)
        second=request(db,assignee_id=4)
        assert second["id"]==first["id"]
        assert second["requested_route_matches_existing"] is False
        assert db.get(CaseAssignment,first["id"]).assignee_id is None
    finally:db.close()

def test_repeated_request_different_title_and_notes_does_not_modify_case():
    db=dataset()
    try:
        first=request(db,title="Officer's signed intake",notes="Original note")
        second=request(db,title="Overwriting title",notes="Overwriting notes")
        case=db.get(CaseAssignment,first["id"])
        assert second["existing"] is True
        assert second["requested_route_matches_existing"] is True
        assert case.title=="Officer's signed intake"
        assert case.notes=="Original note"
        assert case.created_by==1
    finally:db.close()

def test_duplicate_request_has_no_case_mutating_sql_or_new_audit_event():
    db=dataset()
    try:
        first=request(db)
        before=db.query(CaseTransition).count()
        statements=[]
        def record(conn,cursor,statement,params,context,many):
            statements.append(statement.lstrip().lower())
        event.listen(db.get_bind(),"before_cursor_execute",record)
        try:
            second=request(db)
        finally:
            event.remove(db.get_bind(),"before_cursor_execute",record)
        assert second["existing"] is True
        assert db.query(CaseTransition).count()==before
        assert not any(sql.startswith(("insert ","update ","delete ")) for sql in statements)
    finally:db.close()

def test_replay_with_invalid_receiving_department_fails_before_lock():
    db=dataset()
    try:
        request(db)
        with patch.object(casework,"_lock_assignment_source") as lock:
            with pytest.raises(HTTPException) as exc:
                request(db,department="Not an approved department")
        assert exc.value.status_code==422
        lock.assert_not_called()
    finally:db.close()

def test_unconfirmed_incident_province_fails_before_lock():
    db=dataset()
    try:
        with patch.object(casework,"_lock_assignment_source") as lock:
            with pytest.raises(HTTPException) as exc:
                request(db,target_scope="PROVINCE",target_province="Riau")
        assert exc.value.status_code==422
        lock.assert_not_called()
    finally:db.close()

def test_source_permission_and_relevance_validated_before_reuse():
    db=dataset()
    try:
        first=request(db)
        from app.models import EvidenceAssessment
        relevant=db.query(EvidenceAssessment).filter_by(campaign_id=90,result_id=11).first()
        relevant.relevance_label="IRRELEVANT"
        db.commit()
        with patch.object(casework,"_lock_assignment_source") as lock:
            with pytest.raises(HTTPException) as exc:
                request(db)
        assert exc.value.status_code==422
        lock.assert_not_called()
        assert db.get(CaseAssignment,first["id"]).status=="OPEN"
    finally:db.close()

def test_closed_case_kept_historically_and_new_creation_uses_source_lock():
    db=dataset()
    try:
        first=request(db)
        case=db.get(CaseAssignment,first["id"])
        case.status="CLOSED"
        db.commit()
        new=request(db)
        assert new["id"]!=first["id"]
        assert new["existing"] is False
        assert new["requested_route_matches_existing"] is True
        assert db.query(CaseAssignment).count()==2
        assert db.get(CaseAssignment,first["id"]).status=="CLOSED"
    finally:db.close()

def test_unrelated_case_source_never_reused():
    db=dataset()
    try:
        first=request(db)
        with pytest.raises(HTTPException) as exc:
            request(db,source_id="999999")
        assert exc.value.status_code in (403,422)
        assert db.query(CaseAssignment).count()==1
        assert first["id"]==1
    finally:db.close()
