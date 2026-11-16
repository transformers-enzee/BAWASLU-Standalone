"""v158.2: reproducible SQLite management-report query/latency benchmark.

This is a synthetic local SQLite workload, NOT an observed Supabase p95.
"""
import json
from datetime import datetime,timedelta
from time import perf_counter
from sqlalchemy import event
from app.models import User
from app.access import profile
from app.casework import CaseAssignment,CaseReport,CaseTransition
from app.management_reporting import build_briefing,briefing_activity_csv
from test_management_briefings_v1468 import dataset


def add_workload(db,count=420):
    now=datetime.utcnow()-timedelta(minutes=3)
    common=dict(source_type="SOCIAL",source_url="https://example.invalid/post",
      originating_scope="NATIONAL",target_scope="NATIONAL",
      target_department="Penanganan Pelanggaran",created_by=1)
    for cid in range(1000,1000+count):
        db.add(CaseAssignment(id=cid,title="Synthetic activity",
            source_id=str(cid),status="IN_REVIEW",created_at=now,
            source_excerpt="Synthetic data only",notes="SENSITIVE_NOT_FOR_REPORTING",
            tags_json='["not in reporting SQL"]',**common))
        db.add(CaseReport(case_id=cid,title="Synthetic report",status="DRAFT",
            created_by=1,created_at=now,executive_summary="X"*3000))
        db.add(CaseTransition(case_id=cid,actor_id=1,action="REPORT_SUBMITTED",
            happened_at=now))
    db.commit()


def measure(db,fn):
    stmts=[]
    def record(conn,cursor,sql,parameters,context,executemany):
        stmts.append(sql)
    event.listen(db.bind,"before_cursor_execute",record)
    try:
        start=perf_counter()
        result=fn()
        elapsed_ms=round((perf_counter()-start)*1000,2)
    finally:
        event.remove(db.bind,"before_cursor_execute",record)
    return result,stmts,elapsed_ms


def test_query_scaling_is_bounded_and_payload_excludes_large_fields():
    db=dataset()
    try:
        access=profile(db,db.get(User,1))
        baseline,small_sql,small_ms=measure(
            db,lambda:build_briefing(db,access,1,language="en"))
        add_workload(db,420)
        report,large_sql,large_ms=measure(
            db,lambda:build_briefing(db,access,1,language="en"))
        assert baseline["metrics"]["assignments"]==3
        assert report["metrics"]["assignments"]==423
        assert report["metrics"]["report_versions_recorded"]==421
        assert report["metrics"]["approved_reports"]==1
        assert report["period_audit_activity"]["report_submitted_events"]>=420
        assert len(large_sql)<=len(small_sql)+8, (len(small_sql),len(large_sql))
        assert len(large_sql)<=20,len(large_sql)
        grouped=[sql.lower() for sql in large_sql if
                 "join case_transitions" in sql.lower()
                 and "count(" in sql.lower()]
        assert grouped
        selected=grouped[0].split(" from case_assignments",1)[0]
        for field in ("case_assignments.notes","case_assignments.tags_json",
                      "case_assignments.suggested_provinces_json",
                      "case_assignments.updated_at"):
            assert field not in selected,field
        for field in ("case_assignments.title","case_assignments.source_excerpt",
                      "case_assignments.created_by"):
            assert field in selected,field
        report_query=[sql.lower() for sql in large_sql if
            "from case_reports" in sql.lower() and "case_reports.case_id in" in sql.lower()]
        assert len(report_query)==2
        assert all("executive_summary" not in sql for sql in report_query)
        output_bytes=len(json.dumps(report,ensure_ascii=False,default=str).encode("utf-8"))
        assert output_bytes<500000,output_bytes
        print("MANAGEMENT_SQLITE_BENCHMARK "+json.dumps({
            "cohort_cases":423,"small_query_count":len(small_sql),
            "large_query_count":len(large_sql),"small_elapsed_ms":small_ms,
            "large_elapsed_ms":large_ms,"response_json_bytes":output_bytes,
            "database":"synthetic_in_memory_sqlite","production_p95":None},sort_keys=True))
    finally:
        db.close()


def test_activity_csv_large_cohort_keeps_single_row_per_authorized_case():
    db=dataset()
    try:
        add_workload(db,420)
        r,queries,elapsed_ms=measure(
            db,lambda:briefing_activity_csv("weekly","",db.get(User,1),db))
        lines=r.body.decode("utf-8-sig").splitlines()
        assert len(lines)==421
        assert len(queries)<=5,len(queries)
        assert b"SENSITIVE_NOT_FOR_REPORTING" not in r.body
        assert r.headers["Cache-Control"]=="private, no-store"
        print("ACTIVITY_CSV_SQLITE_BENCHMARK "+json.dumps({
            "cases":420,"sql_queries":len(queries),"elapsed_ms":elapsed_ms,
            "csv_bytes":len(r.body),"database":"synthetic_in_memory_sqlite"
        },sort_keys=True))
    finally:
        db.close()
