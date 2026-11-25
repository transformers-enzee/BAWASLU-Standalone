"""Read-only Render image startup must not touch shared Supabase or start workers."""
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "Dockerfile"
WORKFLOW = ROOT / ".github" / "workflows" / "bawaslu-option-b-image.yml"
PUBLISHER = ROOT / ".github" / "workflows" / "bawaslu-staging-image.yml"


def test_read_only_startup_skips_schema_seed_and_background_jobs(monkeypatch):
    from app import main
    monkeypatch.setenv("BAWASLU_STARTUP_READ_ONLY", "1")
    with patch.object(main.Base.metadata, "create_all", side_effect=AssertionError("schema touched")):
        with patch.object(main, "seed", side_effect=AssertionError("seed touched")):
            with patch.object(main, "recover_existing_news_languages", side_effect=AssertionError("data touched")):
                with patch.object(main, "sync_promoted_news_languages", side_effect=AssertionError("data touched")):
                    assert main.startup() is None


def test_safe_image_startup_is_default_and_migrations_opt_in():
    source = DOCKERFILE.read_text(encoding="utf-8")
    assert "ENV BAWASLU_STARTUP_READ_ONLY=1" in source
    assert "then alembic upgrade head || exit 1; fi" in source
    assert "exec uvicorn app.main:app" in source
    workflow = WORKFLOW.read_text(encoding="utf-8")
    triggers = workflow.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in triggers
    assert "\n  push:" not in triggers
    assert 'test -f Dockerfile' in workflow
    publisher = PUBLISHER.read_text(encoding="utf-8")
    assert "\n  push:\n    branches:\n      - architecture-v2-foundation-20261015\n" in publisher
    assert "context: ." in publisher
    assert "BAWASLU_BUILD_VERSION=" in publisher
    assert "BAWASLU_BUILD_COMMIT=" in publisher
    assert "github.ref == 'refs/heads/architecture-v2-foundation-20261015'" in publisher
