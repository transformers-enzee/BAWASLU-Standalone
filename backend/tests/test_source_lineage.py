from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app import source_lineage as module

def user():
    return SimpleNamespace(id=1)

def grant():
    return {"status":"Active","permissions":{"view_intelligence":True},"geographic_scope":"Nationwide"}

class FakeDb:
    def __init__(self,row=None,record=None):
        self.row=row
        self.record=record
    def get(self,cls,key):
        if cls is module.SocialListeningResult:
            return self.row if key==101 else None
        if cls is module.IntelligenceItem:
            return self.record if key==4 else None
        return None

def test_resolver_denies_viewer_without_permission(monkeypatch):
    monkeypatch.setattr(module,"profile",lambda db,user:{"status":"Active","permissions":{"view_intelligence":False}})
    with pytest.raises(HTTPException) as err:
        module.resolve_source("social:101",user(),FakeDb())
    assert err.value.status_code==403

def test_resolver_rejects_noncanonical_ids(monkeypatch):
    monkeypatch.setattr(module,"profile",lambda db,user:grant())
    with pytest.raises(HTTPException) as err:
        module.resolve_source("social:00101",user(),FakeDb())
    assert err.value.status_code==422

def test_resolver_refuses_cross_store_lookup(monkeypatch):
    monkeypatch.setattr(module,"profile",lambda db,user:grant())
    with pytest.raises(HTTPException) as err:
        module.resolve_source("radar:POST-001",user(),FakeDb())
    assert err.value.status_code==409

def test_resolver_scopes_source_before_returning(monkeypatch):
    monkeypatch.setattr(module,"profile",lambda db,user:grant())
    monkeypatch.setattr(module,"_result_in_scope",lambda db,p,row:False)
    row=SimpleNamespace(id=101)
    with pytest.raises(HTTPException) as err:
        module.resolve_source("social:101",user(),FakeDb(row))
    assert err.value.status_code==404

def test_resolver_does_not_claim_source_verification(monkeypatch):
    monkeypatch.setattr(module,"profile",lambda db,user:grant())
    monkeypatch.setattr(module,"_result_in_scope",lambda db,p,row:True)
    row=SimpleNamespace(id=101,provider_result_id="",canonical_url="https://example.org/p",
      platform="threads",published_at="",collected_at=None,text_content="Original",
      observed_handle="@public",author_name="",review_state="PROMOTED",promoted_intelligence_id=4)
    intel=SimpleNamespace(id=4,intelligence_id="INT-4",source_id="")
    result=module.resolve_source("social:101",user(),FakeDb(row,intel))
    assert result["canonical_source_id"]=="social:101"
    assert result["intelligence"]["id"]=="4"
    assert result["publication_time_verified"] is False
    assert result["source_evidence_verified"] is False
    assert "Original" not in str(result)
