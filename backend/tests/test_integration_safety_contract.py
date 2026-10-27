"""Contract tests: the integration inspector cannot trigger paid calls or leak source content.

These tests use no provider credentials and no hosted database.
"""
from pathlib import Path
from app import integration_readiness as integration

def test_all_inspector_sql_is_aggregate_only():
    for name,statement in integration.METRICS.items():
        upper=statement.upper()
        assert "COUNT(" in upper, name
        assert "SELECT *" not in upper, name
        for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "TRUNCATE "):
            assert forbidden not in upper, (name,forbidden)

def test_readiness_router_never_performs_provider_requests():
    source=Path(integration.__file__).read_text(encoding="utf-8")
    for forbidden in ("httpx.post(", "requests.post(", "execute_search(", "assess_pending_campaign(", "process_batch("):
        assert forbidden not in source

def test_source_backfill_always_restricts_nonblank_rows():
    from scripts import backfill_source_ids as backfill
    assert "source_id IS NULL OR TRIM(source_id)=''" in str(backfill.UPDATE)
    assert "promoted_intelligence_id" in str(backfill.FIND)
    assert "LOCK TABLE social_listening_results" in Path(backfill.__file__).read_text(encoding="utf-8")
