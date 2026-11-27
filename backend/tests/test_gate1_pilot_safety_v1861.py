"""Offline, mandatory v186.1 strict QA-only staging pilot safety guards."""
from pathlib import Path
from types import SimpleNamespace

from app import inbox_human_corrections as pilot


def _admin_profile():
    return {
        "id":"701", "name":"QA administrator", "status":"Active",
        "role":"National Administrator", "geographic_scope":"Nationwide",
        "permissions":{
            "administration":True,"human_validation":True,
            "edit_intelligence":True,"view_intelligence":True,
        },
    }


def test_pilot_allowlist_never_enables_operational_campaign(monkeypatch):
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE","staging")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS","12")
    p=_admin_profile()
    qa=SimpleNamespace(id=12,name=pilot.PILOT_QA_CAMPAIGN_NAME,
                       status="DRAFT",created_by="701")
    assert pilot.can_edit_gate1(p,qa)
    assert not pilot.can_edit_gate1(p,SimpleNamespace(
        id=12,name="Real election campaign",status="DRAFT",created_by="701"))
    assert not pilot.can_edit_gate1(p,SimpleNamespace(
        id=12,name=pilot.PILOT_QA_CAMPAIGN_NAME,
        status="ACTIVE",created_by="701"))
    assert not pilot.can_edit_gate1(p,SimpleNamespace(
        id=99,name=pilot.PILOT_QA_CAMPAIGN_NAME,
        status="DRAFT",created_by="701"))
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","false")
    assert not pilot.can_edit_gate1(p,qa)
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_WRITE_ENABLED","true")
    monkeypatch.setenv("BAWASLU_INBOX_GATE1_PILOT_MODE","production")
    assert not pilot.can_edit_gate1(p,qa)


def test_synthetic_provider_requires_provider_and_unique_qa_source_key():
    assert pilot.is_pilot_qa_source(SimpleNamespace(
        provider="GATE1_QA_SYNTHETIC",provider_result_id="GATE1-QA-FICTIONAL-001"))
    assert not pilot.is_pilot_qa_source(SimpleNamespace(
        provider="SOCIALCRAWL",provider_result_id="GATE1-QA-FICTIONAL-001"))
    assert not pilot.is_pilot_qa_source(SimpleNamespace(
        provider="GATE1_QA_SYNTHETIC",provider_result_id="REAL-POST-001"))
    assert not pilot.is_pilot_qa_source(SimpleNamespace(
        provider=None,provider_result_id=None))


def test_staging_preflight_ui_is_read_only_and_no_paid_provider_calls():
    root=Path(__file__).resolve().parents[2]
    ui=(root/"frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    client=(root/"frontend/src/api/base44Client.js").read_text()
    source=(root/"backend/app/inbox_human_gate.py").read_text()
    gate_source=(root/"backend/app/inbox_human_corrections.py").read_text()
    assert "gate1-qa-pilot-preflight" in ui
    assert "gate1-check-pilot-readiness" in ui
    assert "gate1-pilot-readiness-report" in ui
    assert "inboxHumanReview.pilotReadiness" in ui
    assert "pilotReadiness:campaignId" in client
    assert "ready_for_write_pilot" in source
    assert "synthetic_source_count" in source
    assert "non_synthetic_link_count" in source
    assert "is_pilot_qa_source(source)" in gate_source
    assert "PILOT_QA_CAMPAIGN_NAME" in gate_source
    assert "official_insight_published" in gate_source
    assert "model_training_triggered" in gate_source
    assert "db.delete(" not in gate_source
