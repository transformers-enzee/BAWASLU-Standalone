"""v184.9 staging pilot isolation, read-only QA, audit and source guards."""
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.governance_persistence import (
    _pilot_campaign_ids, _write_pilot, _read_enabled, _enabled, _append_governance_audit,
    _source, _sentiment_review_conflicts, submit_override, decide_insight, propose_insight,
    governance_review_queue, list_insights, approved_command_centre, governance_readiness,
    list_overrides, effective_information,
)
from app.models import AuditEvent

def test_read_only_qa_works_when_write_flag_is_off(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED","true")
    monkeypatch.delenv("BAWASLU_GOVERNANCE_WRITES_ENABLED",raising=False)
    assert _read_enabled() is None
    with pytest.raises(HTTPException) as error:_enabled()
    assert error.value.status_code==503
    for endpoint in (list_overrides,list_insights,approved_command_centre,effective_information):
        assert "_read_enabled()" in inspect.getsource(endpoint)

def test_writes_fail_closed_without_explicit_pilot_configuration(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_WRITES_ENABLED","true")
    monkeypatch.delenv("BAWASLU_GOVERNANCE_PILOT_MODE",raising=False)
    monkeypatch.delenv("BAWASLU_GOVERNANCE_PILOT_CAMPAIGN_IDS",raising=False)
    with pytest.raises(HTTPException) as error:_write_pilot(1)
    assert error.value.status_code==503
    monkeypatch.setenv("BAWASLU_GOVERNANCE_PILOT_MODE","staging")
    with pytest.raises(HTTPException) as error:_write_pilot(1)
    assert error.value.status_code==403

@pytest.mark.parametrize("ids",["","all","*","1,2,2","0","-1","1,,invalid",
                                ",".join(str(i) for i in range(1,12))])
def test_malformed_campaign_allowlists_are_denied(monkeypatch,ids):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_PILOT_CAMPAIGN_IDS",ids)
    assert _pilot_campaign_ids()==set()

def test_pilot_only_allows_named_campaign(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_WRITES_ENABLED","true")
    monkeypatch.setenv("BAWASLU_GOVERNANCE_PILOT_MODE","staging")
    monkeypatch.setenv("BAWASLU_GOVERNANCE_PILOT_CAMPAIGN_IDS","6,12")
    assert _write_pilot(6) is None
    with pytest.raises(HTTPException) as error:_write_pilot(99)
    assert error.value.status_code==403

def test_every_write_route_contains_pilot_scope_check():
    assert "_write_pilot(body.campaign_id)" in inspect.getsource(submit_override)
    assert "_write_pilot(body.campaign_id)" in inspect.getsource(propose_insight)
    assert "_write_pilot(row.campaign_id)" in inspect.getsource(decide_insight)

def test_watchlist_only_source_is_not_normal_governance_evidence():
    src=inspect.getsource(_source)
    assert 'CampaignEvidence.match_method!="WATCHLIST_ACCOUNT"' in src

def test_audit_event_is_batched_without_auto_commit():
    db=MagicMock()
    p={"id":"22","name":"Sample reviewer"}
    _append_governance_audit(db,p,"GovernanceInsight",9,"GOVERNANCE_INSIGHT_APPROVED",
                             {"revision":2})
    obj=db.add.call_args.args[0]
    assert isinstance(obj,AuditEvent)
    assert obj.actor_id=="22"
    assert obj.action=="GOVERNANCE_INSIGHT_APPROVED"
    assert '"revision": 2' in obj.changes_json
    db.commit.assert_not_called()

def test_gate_approval_requires_consistent_sentiment_ledgers():
    assert "_sentiment_review_conflicts" in inspect.getsource(decide_insight)
    assert "REVIEW_LEDGER_CONFLICT" in inspect.getsource(governance_review_queue)
    assert "_sentiment_review_conflicts" in inspect.getsource(approved_command_centre)

def test_readiness_schema_is_qualified_to_public():
    src=inspect.getsource(governance_readiness)
    assert "n.nspname='public'" in src
    assert "pilot_writes_ready" in src
