"""v185.5: Inbox Human Gate 1 deep links, source scope, and opt-in correction QA."""
import inspect
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app import inbox_human_gate as lane
from app.models import MonitoringCampaign, SocialListeningResult

def test_lane_is_off_by_default(monkeypatch):
    monkeypatch.delenv("BAWASLU_INBOX_GATE1_READ_ENABLED",raising=False)
    with pytest.raises(HTTPException) as e:lane._read_enabled()
    assert e.value.status_code==503

def test_read_flag_does_not_enable_corrections(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.delenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED",raising=False)
    assert lane._read_enabled() is None
    assert lane._write_enabled() is False

def test_list_campaigns_scoped_to_officer(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.setattr(lane,"_grant",lambda db,user,permission:{"id":"1"})
    monkeypatch.setattr(lane,"allowed",lambda p,c:c.id==10)
    db=MagicMock()
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value=[
      MonitoringCampaign(id=10,name="Authorized",province="Jawa Barat",regency_city="Bandung"),
      MonitoringCampaign(id=11,name="Other",province="DKI Jakarta",regency_city="")]
    r=lane.review_campaigns(user=SimpleNamespace(id=1),db=db)
    assert [c["id"] for c in r["campaigns"]]==["10"]
    assert r["read_only"]
    db.commit.assert_not_called()

def test_sample_enforces_campaign_scope_and_is_not_normal_inbox(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.setattr(lane,"_grant",lambda db,user,permission:{"id":"1"})
    monkeypatch.setattr(lane,"_campaign",lambda db,p,cid:MonitoringCampaign(id=cid))
    monkeypatch.setattr(lane,"information_qa_sample",lambda db,p,cid:{"scanned_count":2,"items":[{"result_id":"1442","action":"SPOT_CHECK_EXCLUDED"}],"not_population_totals":True})
    db=MagicMock()
    r=lane.review_sample(10,user=SimpleNamespace(id=1),db=db)
    assert r["items"][0]["result_id"]=="1442"
    assert r["separate_from_standard_inbox"] is True
    assert r["no_automatic_publication"] is True
    db.commit.assert_not_called()

def test_exact_source_uses_existing_protected_source_helper(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.delenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED",raising=False)
    monkeypatch.setattr(lane,"_grant",lambda db,user,permission:{"id":"1"})
    monkeypatch.setattr(lane,"_campaign",lambda db,p,cid:MonitoringCampaign(id=cid,name="Authorized"))
    calls=[]
    def source(db,p,cid,rid):
        calls.append((cid,rid))
        return SocialListeningResult(id=1442,platform="facebook",text_content="Election discussion",
          author_name="Saved author",canonical_url="https://example.org/post",published_at="2026-11-26")
    monkeypatch.setattr(lane,"_source",source)
    db=MagicMock()
    db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value=None
    r=lane.review_source(10,1442,user=SimpleNamespace(id=1),db=db)
    assert calls==[(10,1442)]
    assert r["text_content"]=="Election discussion"
    assert r["relevance"]=="UNASSESSED"
    assert r["can_correct_relevance"] is False
    assert r["official_insight_approval_required"] is True
    db.commit.assert_not_called()

def test_source_rejects_out_of_scope_without_disclosure(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_READ_ENABLED","true")
    monkeypatch.setattr(lane,"_grant",lambda db,user,permission:{"id":"1"})
    monkeypatch.setattr(lane,"_campaign",lambda db,p,cid:MonitoringCampaign(id=cid))
    def deny(db,p,cid,rid):raise HTTPException(404,"Source unavailable")
    monkeypatch.setattr(lane,"_source",deny)
    with pytest.raises(HTTPException) as e:lane.review_source(10,999,user=SimpleNamespace(id=1),db=MagicMock())
    assert e.value.status_code==404

def test_frontend_routes_gate1_without_changing_standard_eligibility():
    root=Path(__file__).resolve().parents[2]
    inbox=(root/"frontend"/"src"/"pages"/"Inbox.jsx").read_text()
    review=(root/"frontend"/"src"/"pages"/"GovernanceReview.jsx").read_text()
    laneui=(root/"frontend"/"src"/"components"/"intel"/"InboxHumanReview.jsx").read_text()
    assert "params.get('gate1')==='1'" in inbox
    assert "<StandardInbox/>" in inbox
    assert "gate1=1&campaign_id=" in review
    assert "base44.inboxHumanReview.source" in laneui
    assert "campaignAssessmentCorrection" in laneui
    assert "detail.can_correct_relevance" in laneui
    assert "originalLink(detail.canonical_url)" in laneui
    assert "OFFICER_CORRECTION" not in inbox[:4000]
    assert 'data-testid="inbox-human-gate1"' in laneui

def test_gate1_write_control_is_separate_from_existing_command_centre():
    source=inspect.getsource(lane.review_source)
    from app.inbox_human_corrections import can_edit_gate1
    control=inspect.getsource(can_edit_gate1)
    assert 'can_edit_gate1(officer,campaign)' in source
    assert '_source(db,officer,campaign_id,result_id)' in source
    assert '_write_enabled()' in control
    assert 'BAWASLU_INBOX_GATE1_PILOT_MODE' in control
    assert 'human_validation' in control
    assert '_editable(profile, campaign)' in control
