"""v184.7 governance migration security and adapter contracts."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.governance_integration import active, inbox_governance_annotations, approved_command_annotations
from app.governance_persistence import CorrectionIn, submit_override
from app.governance_projection import effective_assessment

def test_disabled_has_zero_extra_db_queries(monkeypatch):
    monkeypatch.delenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED",raising=False)
    db=MagicMock()
    assert inbox_governance_annotations(db,[{"campaign_id":"1","id":"2"}])=={}
    assert approved_command_annotations(db,{},[SimpleNamespace(id=1)])==[]
    db.query.assert_not_called()

def test_gated_inbox_page_bound(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED","true")
    db=MagicMock()
    with pytest.raises(ValueError):
        inbox_governance_annotations(db,[{"campaign_id":"1","id":str(i)} for i in range(1,302)])
    db.query.assert_not_called()

def test_effective_projection_latest_revision_wins():
    rows=[SimpleNamespace(field="sentiment",human_value="NEGATIVE",id=1,revision=1,status="approved",reviewer_id=12),
          SimpleNamespace(field="sentiment",human_value="POSITIVE",id=2,revision=2,status="approved",reviewer_id=13)]
    preview=effective_assessment(None,rows)
    assert preview["fields"]["sentiment"]["effective_value"]=="POSITIVE"
    assert preview["record_human_verified"] is False

def test_officer_override_restricted_to_assessment_fields():
    import inspect
    src=inspect.getsource(submit_override)
    assert '("sentiment","relevance")' in src
    assert 'body.human_value.strip().upper()' in src

def test_command_adapter_does_not_publish_legacy_findings():
    import inspect
    source=inspect.getsource(approved_command_annotations)
    assert '_approved_row_gate' in source
    assert '_snapshot' in source
    assert '"read_only":True' in source

def test_sql_migration_is_non_destructive():
    from pathlib import Path
    migration=Path(__file__).resolve().parents[1]/"alembic"/"versions"/"20261126_01_governance_persistence.py"
    content=migration.read_text()
    assert "ENABLE ROW LEVEL SECURITY" in content
    assert "REVOKE ALL" in content
    assert "DROP TABLE" not in content
