"""v185.2: controlled admin QA-only read activation and balanced information QA."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import inspect
import pytest
from fastapi import HTTPException
from app import governance_persistence as governance
from app.governance_information_qa import balanced_review_sample

def test_qa_flag_does_not_enable_normal_read_or_writes(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_QA_READ_ENABLED","true")
    monkeypatch.delenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED",raising=False)
    monkeypatch.delenv("BAWASLU_GOVERNANCE_WRITES_ENABLED",raising=False)
    assert governance._qa_read_enabled() is None
    with pytest.raises(HTTPException) as a: governance._read_enabled()
    assert a.value.status_code==503
    with pytest.raises(HTTPException) as b: governance._enabled()
    assert b.value.status_code==503

def test_qa_flag_does_not_expose_review_queue_to_non_admin(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_QA_READ_ENABLED","true")
    monkeypatch.delenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED",raising=False)
    monkeypatch.setattr(governance,"_grant",lambda db,user,permission: (_ for _ in ()).throw(HTTPException(403,"Not an administrator")) if permission=="administration" else {"permissions":{"view_intelligence":True}})
    with pytest.raises(HTTPException) as err:
        governance.governance_review_queue(campaign_id=1,limit=5,user=SimpleNamespace(id=1),db=MagicMock())
    assert err.value.status_code==403

def test_qa_flag_fails_closed_when_absent_even_if_general_reads_on(monkeypatch):
    monkeypatch.delenv("BAWASLU_GOVERNANCE_QA_READ_ENABLED",raising=False)
    monkeypatch.setenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED","true")
    with pytest.raises(HTTPException) as err: governance._qa_read_enabled()
    assert err.value.status_code==503

def test_admin_campaign_scopes_are_checked(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_QA_READ_ENABLED","true")
    monkeypatch.setattr(governance,"_grant",lambda db,user,permission:{"id":"1","status":"Active"})
    monkeypatch.setattr(governance,"allowed",lambda profile,record:record.id==1)
    db=MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value=[
        SimpleNamespace(id=1,name="Authorized",province="Region A",jurisdiction_type="Province"),
        SimpleNamespace(id=2,name="Out of scope",province="Region B",jurisdiction_type="Province")]
    result=governance.governance_qa_campaigns(user=SimpleNamespace(id=1),db=db)
    assert [r["id"] for r in result["campaigns"]]==[1]
    assert result["paid_provider_called"] is False
    db.commit.assert_not_called()

def test_admin_summary_can_be_read_with_general_flag_off(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_QA_READ_ENABLED","true")
    monkeypatch.delenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED",raising=False)
    monkeypatch.setattr(governance,"_grant",lambda db,user,permission:{"id":"1","status":"Active","permissions":{"view_intelligence":True,"administration":True}})
    monkeypatch.setattr(governance,"_campaign",lambda db,p,campaign_id:SimpleNamespace(id=campaign_id))
    monkeypatch.setattr(governance,"governance_review_queue",lambda **kw:{
        "cases":[],"awaiting_review":0,"needs_reassessment":0})
    import app.governance_information_qa as qa
    monkeypatch.setattr(qa,"information_qa_sample",lambda db,p,campaign_id:{"scanned_count":3,"items":[]})
    db=MagicMock()
    result=governance.governance_qa_campaign_summary(campaign_id=1,user=SimpleNamespace(id=1),db=db)
    assert result["information_qa"]["scanned_count"]==3
    assert result["manual_qa_authorized"] is False
    db.commit.assert_not_called()

def test_balanced_sample_includes_all_review_categories():
    actions=["VERIFY_UNASSESSED"]*40+["REVIEW_UNCERTAIN"]*9+["SPOT_CHECK_EXCLUDED"]*8+["CHECK_RELEVANT_EVIDENCE"]*25
    records=[{"action":a,"result_id":str(i)} for i,a in enumerate(actions)]
    result=balanced_review_sample(records,20)
    assert len(result)==20
    assert set(x["action"] for x in result)==set(actions)
    assert len(set(x["result_id"] for x in result))==20

def test_qa_activation_keeps_mutating_gate_closed():
    for f in (governance.submit_override,governance.propose_insight,governance.decide_insight):
        assert "_write_pilot(" in inspect.getsource(f)
    source=inspect.getsource(governance.governance_qa_campaign_summary)
    assert '_qa_read_enabled()' in source
    assert '_grant(db,user,"administration")' in source
    assert '_campaign(db,p,campaign_id)' in source
    assert "db.commit(" not in source

def test_frontend_uses_qa_only_flag():
    from pathlib import Path
    page=(Path(__file__).resolve().parents[2]/"frontend"/"src"/"pages"/"GovernanceReview.jsx").read_text()
    assert "governance_qa_reads_enabled" in page
    assert "governance_reads_enabled" not in page
    assert 'data-testid="governance-information-qa"' in page

def test_real_campaign_model_has_no_jurisdiction_type_and_list_does_not_500(monkeypatch):
    """Regression: real SQLAlchemy model previously raised AttributeError on row.jurisdiction_type."""
    from app.models import MonitoringCampaign
    import app.governance_persistence as governance
    model=MonitoringCampaign(id=23,name="Election Campaign",province="Jawa Barat",regency_city="Bandung")
    assert "jurisdiction_type" not in MonitoringCampaign.__mapper__.attrs.keys()
    monkeypatch.setenv("BAWASLU_GOVERNANCE_QA_READ_ENABLED","true")
    monkeypatch.setattr(governance,"_grant",lambda db,user,permission:{"id":"1","status":"Active"})
    monkeypatch.setattr(governance,"allowed",lambda profile,row:True)
    db=MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value=[model]
    data=governance.governance_qa_campaigns(user=SimpleNamespace(id=1),db=db)
    assert data["campaigns"]==[{"id":23,"name":"Election Campaign","province":"Jawa Barat","regency_city":"Bandung"}]
    assert data["available_count"]==1
    assert data["read_only"] is True
    db.commit.assert_not_called()


def test_campaign_list_never_reads_unmapped_jurisdiction_type():
    from app.models import MonitoringCampaign
    source=inspect.getsource(governance.governance_qa_campaigns)
    assert "row.jurisdiction_type" not in source
    for attr in ("id","name","province","regency_city"):
        assert attr in MonitoringCampaign.__mapper__.attrs.keys()


def test_ui_load_error_does_not_claim_no_authorized_campaigns():
    from pathlib import Path
    page=(Path(__file__).resolve().parents[2]/"frontend"/"src"/"pages"/"GovernanceReview.jsx").read_text()
    assert 'setCampaigns([]);setTruncated(false);setSelected(\'\');' in page
    assert '!error?<p className="text-sm text-slate-600">' in page
    assert "Campaigns could not be loaded." in page
