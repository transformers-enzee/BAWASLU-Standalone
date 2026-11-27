"""v186.6: isolated Render QA database bootstrap regression."""
import os
from urllib.parse import quote_plus

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import engine
from app.models import (
    AuditEvent, CampaignEvidence, EvidenceAssessment, MonitoringCampaign,
    SocialListeningResult, User,
)
from scripts.seed_gate1_render_qa_v1866 import (
    ADMIN_EMAIL, EXPECTED_KEYS, QA_DATABASE, QA_DB_USER, VIEWER_EMAIL,
    assert_isolated_qa_database, bootstrap,
)


def test_qa_bootstrap_rejects_operational_and_other_targets(monkeypatch):
    monkeypatch.setenv("BAWASLU_GATE1_QA_ISOLATED", "YES")
    monkeypatch.setenv("BAWASLU_GATE1_QA_BOOTSTRAP", "YES")
    monkeypatch.setenv("BAWASLU_STARTUP_READ_ONLY", "1")
    monkeypatch.delenv("BAWASLU_ALLOW_ISOLATED_DB_TEST", raising=False)
    targets = [
        "postgresql://postgres:secret@db.bsekqkhgyjedcmptjnag.supabase.co:5432/postgres",
        f"postgresql://{QA_DB_USER}:secret@127.0.0.1:5432/{QA_DATABASE}",
        f"postgresql://{QA_DB_USER}:secret@db.supabase.co:5432/{QA_DATABASE}",
        f"postgresql://postgres:secret@dpg-fake.singapore-postgres.render.com:5432/{QA_DATABASE}",
        f"postgresql://{QA_DB_USER}:secret@dpg-fake.singapore-postgres.render.com:5432/postgres",
        "sqlite:///qa.db",
    ]
    for target in targets:
        with pytest.raises(SystemExit, match="REFUSED"):
            assert_isolated_qa_database(target)
    with pytest.raises(SystemExit, match="REFUSED"):
        assert_isolated_qa_database("")


def test_qa_bootstrap_requires_explicit_flags(monkeypatch):
    target = f"postgresql://{QA_DB_USER}:secret@dpg-fake.singapore-postgres.render.com:5432/{QA_DATABASE}"
    for key in ("BAWASLU_GATE1_QA_ISOLATED", "BAWASLU_GATE1_QA_BOOTSTRAP"):
        monkeypatch.setenv("BAWASLU_GATE1_QA_ISOLATED", "YES")
        monkeypatch.setenv("BAWASLU_GATE1_QA_BOOTSTRAP", "YES")
        monkeypatch.delenv(key, raising=False)
        with pytest.raises(SystemExit, match="REFUSED"):
            assert_isolated_qa_database(target)


def test_persistent_qa_seed_and_idempotence_on_disposable_postgres(monkeypatch):
    if os.getenv("BAWASLU_ALLOW_ISOLATED_DB_TEST") != "YES":
        pytest.skip("Only opt-in disposable localhost Postgres runs this integration")
    monkeypatch.setenv("BAWASLU_GATE1_QA_ISOLATED", "YES")
    monkeypatch.setenv("BAWASLU_GATE1_QA_BOOTSTRAP", "YES")
    monkeypatch.setenv("BAWASLU_STARTUP_READ_ONLY", "1")
    bootstrap()
    with Session(engine) as db:
        campaign = db.scalar(select(MonitoringCampaign))
        assert campaign and campaign.id == 1 and campaign.status == "DRAFT"
        assert db.scalar(select(func.count()).select_from(CampaignEvidence)) == 7
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment)) == 5
        assert {row.provider_result_id for row in db.scalars(select(SocialListeningResult))} == EXPECTED_KEYS
        assert {row.email for row in db.scalars(select(User))} == {ADMIN_EMAIL, VIEWER_EMAIL}
        assert db.scalar(select(func.count()).select_from(AuditEvent)) == 0
        assert all(row.promoted_intelligence_id is None
                   for row in db.scalars(select(SocialListeningResult)))
    bootstrap()  # Must not add, reset or overwrite officer information.
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(CampaignEvidence)) == 7
        assert db.scalar(select(func.count()).select_from(EvidenceAssessment)) == 5
