"""Verify the new packaging target never bypasses the same-commit backend gate."""
from pathlib import Path

def test_staging_publisher_requires_backend_and_keeps_manual_docker_gate():
    root=Path(__file__).resolve().parents[2]
    workflow=(root/'.github/workflows/bawaslu-staging-image.yml').read_text()
    docker=(root/'Dockerfile').read_text()
    assert 'needs: backend-regression' in workflow
    assert 'run: pytest -q' in workflow
    assert 'target: runtime' in workflow
    assert 'FROM runtime AS verified' in docker
    assert 'COPY --from=backend-qa /tmp/bawaslu-backend-qa-passed' in docker
    assert docker.index('RUN pip install') < docker.index('ARG BAWASLU_BUILD_VERSION')
    assert 'ENV BAWASLU_STARTUP_READ_ONLY=1' in docker
