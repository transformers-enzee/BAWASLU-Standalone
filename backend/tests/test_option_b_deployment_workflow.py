"""Static no-cost Option B guardrails; does not contact Render or GHCR."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "bawaslu-option-b-image.yml"
DOCS = ROOT / "docs" / "bawaslu-option-b-staging.md"


def test_option_b_build_is_staging_only_and_no_automatic_render_deploy():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "branches: [architecture-v2-foundation-20261015]" in content
    assert "paths:\n      - '.github/workflows/bawaslu-option-b-image.yml'" in content
    assert "github.ref == 'refs/heads/architecture-v2-foundation-20261015'" in content
    assert "deploy_staging == true" in content
    assert "default: false" in content
    assert "BAWASLU_STAGING_IMAGE_READY" in content
    assert "RENDER_STAGING_DEPLOY_HOOK" in content


def test_option_b_uses_immutable_image_and_no_render_build():
    content = WORKFLOW.read_text(encoding="utf-8")
    assert "ghcr.io/transformers-enzee/bawaslu-standalone:sha-" in content
    assert "platforms: linux/amd64" in content
    assert "docker/build-push-action@v6" in content
    assert "packages: write" in content
    assert "imgURL=" in content
    assert "render deploy requested" in content.lower()
    assert "render.yaml" not in content


def test_option_b_doc_requires_database_and_image_source_checks():
    content = DOCS.read_text(encoding="utf-8")
    assert "alembic upgrade head" in content
    assert "staging" in content
    assert "read:packages" in content
    assert "Source → Edit" in content
    assert "Do not create a replacement public service" in content
