"""v186.2 fail-closed CI harness safeguards; full offline regression."""
from pathlib import Path
import os
import pytest
from scripts.seed_gate1_ci_v1862 import assert_local_postgres

URL="postgresql+psycopg://gate1qa:local-only@127.0.0.1:5432/bawaslu_gate1_pilot_ci"


def test_localhost_disposable_postgres_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("BAWASLU_GATE1_ISOLATED_E2E",raising=False)
    monkeypatch.setenv("BAWASLU_ALLOW_ISOLATED_DB_TEST","YES")
    with pytest.raises(SystemExit,match="REFUSED"):
        assert_local_postgres(URL)
    monkeypatch.setenv("BAWASLU_GATE1_ISOLATED_E2E","YES")
    assert_local_postgres(URL)
    monkeypatch.setenv("BAWASLU_ALLOW_ISOLATED_DB_TEST","NO")
    with pytest.raises(SystemExit,match="REFUSED"):
        assert_local_postgres(URL)


@pytest.mark.parametrize("unsafe_url",[
    "postgresql://gate1qa:x@db.example.supabase.co:5432/bawaslu_gate1_pilot_ci",
    "postgresql://gate1qa:x@postgres.render.com:5432/bawaslu_gate1_pilot_ci",
    "postgresql://gate1qa:x@127.0.0.1:5432/bawaslu",
    "postgresql://postgres:x@127.0.0.1:5432/bawaslu_gate1_pilot_ci",
    "postgresql://gate1qa:x@127.0.0.1:6543/bawaslu_gate1_pilot_ci",
    "sqlite:///./bawaslu.db",
])
def test_ci_seed_never_accepts_operational_or_unexpected_database(monkeypatch,unsafe_url):
    monkeypatch.setenv("BAWASLU_GATE1_ISOLATED_E2E","YES")
    monkeypatch.setenv("BAWASLU_ALLOW_ISOLATED_DB_TEST","YES")
    with pytest.raises(SystemExit,match="REFUSED"):
        assert_local_postgres(unsafe_url)


def test_browser_workflow_must_use_ephemeral_db_and_no_live_credentials():
    root=Path(__file__).resolve().parents[2]
    flow=(root/".github/workflows/bawaslu-gate1-browser-pilot.yml").read_text()
    spec=(root/"frontend/e2e/gate1-write-pilot-v1862.spec.js").read_text()
    seed=(root/"backend/scripts/seed_gate1_ci_v1862.py").read_text()
    verify=(root/"backend/scripts/verify_gate1_ci_v1862.py").read_text()
    for expected in (
        "POSTGRES_DB: bawaslu_gate1_pilot_ci",
        "BAWASLU_STARTUP_READ_ONLY: \"true\"",
        "BAWASLU_GATE1_ISOLATED_E2E: \"YES\"",
        "OPENAI_API_KEY: \"\"",
        "SOCIALCRAWL_API_KEY: \"\"",
        "PLAYWRIGHT_BASE_URL: http://127.0.0.1:5173",
        "npx playwright test e2e/gate1-write-pilot-v1862.spec.js",
        "scripts.verify_gate1_ci_v1862",
    ):
        assert expected in flow
    for expected in (
        "test.skip(!enabled", "sourceSnapshot", "REVALIDATION_REQUIRED",
        "GATE1_FIELD_RESTORED", "expect(stale.status()).toBe(409)",
        "toBe(403)", "toBe(401)", "toBe(404)",
        "Original AI relevance",
    ):
        assert expected in spec
    assert "assert_local_postgres(url)" in seed
    assert "not empty" in seed
    assert "assert_local_postgres(url)" in verify
    assert "raw_payload_json" in verify
    assert "IntelligenceItem" in verify
    assert "base44.inboxHumanReview.pilotReadiness" not in seed
