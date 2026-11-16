"""v158.1 management case creation cohort fetches only required columns."""
from datetime import datetime
from sqlalchemy import event
from app.models import User
from app.access import profile
from app.management_reporting import scoped_cases,build_briefing
from test_management_briefings_v1468 import dataset

def test_creation_cohort_query_excludes_unused_notes_and_json():
    db=dataset()
    statements=[]
    def capture(conn,cursor,sql,parameters,context,executemany):
        statements.append(sql.lower())
    try:
        role=profile(db,db.get(User,1))
        event.listen(db.bind,"before_cursor_execute",capture)
        cases,_,_,_=scoped_cases(db,role,1,"weekly")
        assert len(cases)==3
        cohort=[sql for sql in statements if
            "from case_assignments" in sql and "case_assignments.created_at >=" in sql]
        assert cohort
        select=cohort[0].split(" from case_assignments",1)[0]
        for missing in ("case_assignments.notes","case_assignments.tags_json",
                        "case_assignments.suggested_provinces_json","case_assignments.updated_at"):
            assert missing not in select,missing
        for required in ("case_assignments.source_excerpt",
                         "case_assignments.target_province",
                         "case_assignments.created_by"):
            assert required in select,required
    finally:
        event.remove(db.bind,"before_cursor_execute",capture)
        db.close()

def test_loaded_case_fields_used_by_management_do_not_trigger_lazy_reads():
    db=dataset()
    statements=[]
    def capture(conn,cursor,sql,parameters,context,executemany):
        statements.append(sql.lower())
    try:
        role=profile(db,db.get(User,1))
        cases,_,_,_=scoped_cases(db,role,1,"weekly")
        event.listen(db.bind,"before_cursor_execute",capture)
        for row in cases:
            assert row.id>0 and row.title
            _=(row.source_excerpt,row.source_url,row.campaign_id,row.status,
               row.originating_scope,row.originating_province,
               row.target_scope,row.target_province,row.target_department,
               row.verified_province,row.assignee_id,row.created_by,
               row.created_at,row.source_type,row.source_id)
        assert statements==[]
    finally:
        event.remove(db.bind,"before_cursor_execute",capture)
        db.close()

def test_management_kpis_and_topic_filter_remain_unchanged():
    db=dataset()
    try:
        role=profile(db,db.get(User,1))
        report=build_briefing(db,role,1,language="en")
        assert report["metrics"]["assignments"]==3
        assert report["metrics"]["unique_linked_sources"]==2
        assert report["metrics"]["approved_reports"]==1
        cases,_,_,_=scoped_cases(db,role,1,"weekly","Riau")
        assert {row.id for row in cases}=={1,2}
    finally:db.close()

def test_province_scope_respected_with_lightweight_cases():
    db=dataset()
    try:
        access=profile(db,db.get(User,2))
        cases,_,_,_=scoped_cases(db,access,2,"weekly")
        assert {row.id for row in cases}=={1,2}
        report=build_briefing(db,access,2)
        assert report["metrics"]["assignments"]==2
        assert report["metrics"]["approved_reports"]==1
        assert build_briefing(db,access,2,topic="Bali")["metrics"]["assignments"]==0
    finally:db.close()
