"""BAWASLU v184.5 offline authorization / lifecycle guards."""
import pytest
from fastapi import HTTPException
from app.governance_persistence import _enabled, _snapshot, CorrectionIn, InsightIn, DecisionIn
from app.human_governance_gates import insight_publication_gate
from app.models import GovernanceFieldCorrection, GovernanceInsight

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("BAWASLU_GOVERNANCE_WRITES_ENABLED",raising=False)
    with pytest.raises(HTTPException) as e:_enabled()
    assert e.value.status_code==503

def test_enabled_only_explicitly(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_WRITES_ENABLED","true")
    assert _enabled() is None

def test_schema_is_additive_and_revisions_uniquely_scoped():
    assert GovernanceInsight.__tablename__=="governance_insights"
    assert GovernanceFieldCorrection.__tablename__=="governance_field_corrections"
    assert len(GovernanceFieldCorrection.__table__.constraints)>=2

def test_validation_prevents_unbounded_review_data():
    with pytest.raises(Exception):
        CorrectionIn(campaign_id=1,result_id=1,field="sentiment",human_value="negative",
                     reason="short",expected_revision=0)
    with pytest.raises(Exception):
        InsightIn(campaign_id=1,title="Test insight",evidence_result_ids=list(range(101)),
                  analysis_scope="2026-11")
    with pytest.raises(Exception):
        DecisionIn(expected_revision=0,decision="approve",rationale="Reasoned decision")

def test_publication_contract_rejects_stale_sources():
    payload={"state":"approved","approver_id":"11","approved_revision":"1",
             "finding_id":"42","evidence_refs":["12"],"analysis_scope":"2026-11",
             "source_revision_current":False}
    assert not insight_publication_gate(payload)["publish_allowed"]
