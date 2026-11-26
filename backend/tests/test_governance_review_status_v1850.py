"""v185.0 admin-only read QA and route/UX contract regression."""
import inspect
from unittest.mock import MagicMock
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.governance_persistence import governance_qa_campaigns,governance_qa_campaign_summary

def test_admin_campaigns_api_fails_closed_when_read_flag_off(monkeypatch):
    monkeypatch.delenv('BAWASLU_GOVERNANCE_INTEGRATION_ENABLED',raising=False)
    with pytest.raises(HTTPException) as err:
        governance_qa_campaigns(user=SimpleNamespace(id=1),db=MagicMock())
    assert err.value.status_code==503

def test_admin_summary_api_fails_closed_when_read_flag_off(monkeypatch):
    monkeypatch.delenv('BAWASLU_GOVERNANCE_INTEGRATION_ENABLED',raising=False)
    with pytest.raises(HTTPException) as err:
        governance_qa_campaign_summary(campaign_id=1,user=SimpleNamespace(id=1),db=MagicMock())
    assert err.value.status_code==503

def test_only_authorized_campaigns_in_admin_listing():
    s=inspect.getsource(governance_qa_campaigns)
    assert '_grant(db,user,"administration")' in s
    assert '_grant(db,user,"view_intelligence")' in s
    assert 'if allowed(p,row)' in s
    assert '"read_only":True' in s

def test_campaign_summary_uses_scoped_review_queue_not_new_ai_calls():
    s=inspect.getsource(governance_qa_campaign_summary)
    assert '_campaign(db,p,campaign_id)' in s
    assert 'governance_review_queue' in s
    assert '"paid_provider_called":False' in s

def test_reviewer_screen_and_api_use_no_mutation_controls():
    from pathlib import Path
    frontend=Path(__file__).resolve().parents[2]/'frontend'/'src'
    page=(frontend/'pages'/'GovernanceReview.jsx').read_text()
    client=(frontend/'api'/'base44Client.js').read_text()
    nav=(frontend/'App.jsx').read_text()
    assert '/administration/governance-review' in nav
    assert 'permission="administration"' in nav
    assert "base44.governance.readiness()" in page
    assert "base44.governance.qaSummary(selected)" in page
    assert 'request(\'/api/governance/qa/campaigns\',{cache:' in client
    assert 'method:\'POST\'' not in page
    assert 'data-testid="governance-review-page"' in page
