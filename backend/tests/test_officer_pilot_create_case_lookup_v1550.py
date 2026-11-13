"""v155.0 regression: actual officer case-creation duplicate lookup.
Tests use the in-memory SQLite dataset, never connected Supabase.
"""
from sqlalchemy import event
from app.casework import CaseAssignment, CaseTransition
from test_casework_workflow import dataset
from test_officer_pilot_end_to_end_v1545 import request
from test_officer_pilot_active_case_lookup_v1547 import _case


def test_more_than_fifty_old_records_never_create_duplicate_active_case():
    db=dataset()
    try:
        db.add_all([_case(11,status="CLOSED") for _ in range(70)])
        db.add(_case(11))
        db.commit()
        latest=db.query(CaseAssignment).order_by(CaseAssignment.id.desc()).first()
        before=db.query(CaseAssignment).count()
        events=db.query(CaseTransition).count()
        second=request(db)
        assert second["existing"] is True
        assert second["id"]==latest.id
        assert second["assignment_created"] is False
        assert db.query(CaseAssignment).count()==before
        assert db.query(CaseTransition).count()==events
    finally: db.close()


def test_case_creation_duplicate_lookup_uses_one_bounded_sql_selection():
    db=dataset()
    try:
        db.add_all([_case(11) for _ in range(70)])
        db.commit()
        sql=[]
        def capture(conn,cursor,statement,params,context,many):
            if "case_assignments" in statement and statement.lstrip().lower().startswith("select"):
                sql.append(statement)
        event.listen(db.get_bind(),"before_cursor_execute",capture)
        try:
            reused=request(db)
        finally:
            event.remove(db.get_bind(),"before_cursor_execute",capture)
        assert reused["existing"] is True
        assert reused["id"]==70
        assert any("LIMIT" in statement.upper() for statement in sql)
        assert db.query(CaseAssignment).count()==70
    finally: db.close()


def test_another_authorized_officer_reuses_latest_without_creating_event():
    db=dataset()
    try:
        db.add_all([_case(11) for _ in range(65)])
        db.commit()
        before=db.query(CaseTransition).count()
        second=request(db,ident=4)
        assert second["id"]==65
        assert second["existing"] is True
        assert second["assignment_created"] is False
        assert db.query(CaseTransition).count()==before
    finally: db.close()
