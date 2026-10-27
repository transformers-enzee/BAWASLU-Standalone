"""Integration release contracts: sessions, officer gating, canonical lineage.

Static checks ensure critical access-control wiring is present without login
credentials, external API requests or mutations of live evidence.
"""
from pathlib import Path
from app import source_ids
from app import integration_readiness
from app import source_lineage

FRONTEND=Path(__file__).resolve().parents[2]/"frontend"/"src"

def test_source_references_do_not_join_namespaces():
    assert source_ids.canonical_source_id("social",101)=="social:101"
    assert source_ids.canonical_source_id("radar","POST-101")=="radar:POST-101"
    assert source_ids.canonical_candidate_id("2")=="candidate:2"

def test_officer_scoping_remains_enforced():
    source=Path(source_lineage.__file__).read_text(encoding="utf-8")
    assert "_result_in_scope(db,p,row)" in source
    assert 'HTTPException(404,"Source unavailable")' in source
    assert "source_evidence_verified" in source

def test_integration_readiness_never_self_approves_manual_uat():
    source=Path(integration_readiness.__file__).read_text(encoding="utf-8")
    assert '"manual_validation_required":True' in source
    assert '"paid_requests"]=0' in source

def test_authentication_state_and_assistant_history_use_same_session():
    auth=(FRONTEND/"lib"/"AuthContext.jsx").read_text(encoding="utf-8")
    assistant=(FRONTEND/"pages"/"IntelligenceAssistant.jsx").read_text(encoding="utf-8")
    assert "setUser(null)" in auth
    assert "base44.auth.logout('/login')" in auth
    assert "bawaslu_access_token" in assistant
    assert "VITE_API_BASE_URL" in assistant
    assert "response.status===401" in assistant
