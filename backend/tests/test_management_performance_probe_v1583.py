"""v158.3 management performance probe: opt-in, read-only, admin-only."""
import json
import pytest
from fastapi import HTTPException
from app.models import User
from app.management_reporting import management_performance_sample
from app.management_perf import measure_sql
from test_management_briefings_v1468 import dataset


def test_disabled_by_default_returns_404(monkeypatch):
    monkeypatch.delenv("BAWASLU_REPORT_PERF_ENABLED",raising=False)
    db=dataset()
    try:
        with pytest.raises(HTTPException) as e:
            management_performance_sample("weekly",db.get(User,1),db)
        assert e.value.status_code==404
    finally: db.close()


def test_enabled_probe_has_only_safe_aggregate_metadata(monkeypatch):
    monkeypatch.setenv("BAWASLU_REPORT_PERF_ENABLED","1")
    db=dataset()
    try:
        result=management_performance_sample("weekly",db.get(User,1),db)
        assert result["schema"]=="BAWASLU_MANAGEMENT_PERFORMANCE_PROBE_V1583"
        assert result["case_cohort_size"]==3
        assert result["query_count"]>=3
        assert result["db_driver_elapsed_ms"]>=0
        assert result["non_db_elapsed_ms"]>=0
        assert result["total_service_elapsed_ms"]>=result["db_driver_elapsed_ms"]
        assert result["serialized_report_bytes"]>0
        assert result["serialization_elapsed_ms"]>=0
        assert result["max_query_elapsed_ms"]>=0
        assert result["average_query_elapsed_ms"]>=0
        assert result["max_query_elapsed_ms"]<=result["db_driver_elapsed_ms"]+0.002
        assert result["total_instrumented_elapsed_ms"]>=result["total_service_elapsed_ms"]
        assert result["total_instrumented_elapsed_ms"]>=result["serialization_elapsed_ms"]
        assert not result["production_p95_established"]
        assert not result["contains_case_or_report_text"]
        result_text=json.dumps(result)
        for secret in ("example.invalid","Riau alleged","Review note","1@example.invalid"):
            assert secret not in result_text
    finally: db.close()


@pytest.mark.parametrize("uid",[2,3,4])
def test_non_admin_provinces_and_viewer_forbidden(monkeypatch,uid):
    monkeypatch.setenv("BAWASLU_REPORT_PERF_ENABLED","1")
    db=dataset()
    try:
        with pytest.raises(HTTPException) as e:
            management_performance_sample("weekly",db.get(User,uid),db)
        assert e.value.status_code==403
    finally:db.close()


def test_invalid_period_respects_existing_validation(monkeypatch):
    monkeypatch.setenv("BAWASLU_REPORT_PERF_ENABLED","1")
    db=dataset()
    try:
        with pytest.raises(HTTPException) as e:
            management_performance_sample("yearly",db.get(User,1),db)
        assert e.value.status_code==422
    finally:db.close()


def test_db_listener_is_connection_scoped_removed_after_sample():
    db=dataset()
    try:
        with measure_sql(db) as sample:
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
        assert sample["query_count"]==1
        with measure_sql(db) as another:
            db.execute(__import__("sqlalchemy").text("SELECT 2"))
        assert another["query_count"]==1
    finally:db.close()


def test_zero_query_sample_has_zero_query_aggregates():
    db=dataset()
    try:
        with measure_sql(db) as result:
            pass
        assert result["query_count"]==0
        assert result["max_query_elapsed_ms"]==0
        assert result["average_query_elapsed_ms"]==0
        assert result["db_driver_elapsed_ms"]==0
    finally:db.close()


def test_multiple_queries_have_aggregates_and_listener_cleanup():
    from sqlalchemy import text
    db=dataset()
    try:
        with measure_sql(db) as sample:
            for _ in range(3):
                db.execute(text("SELECT 1"))
        assert sample["query_count"]==3
        assert sample["average_query_elapsed_ms"]>=0
        assert sample["max_query_elapsed_ms"]>=0
        with measure_sql(db) as next_sample:
            db.execute(text("SELECT 1"))
        assert next_sample["query_count"]==1
    finally:db.close()
