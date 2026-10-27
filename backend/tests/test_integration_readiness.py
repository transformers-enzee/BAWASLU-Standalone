"""Integration readiness endpoint permission and read-only evidence checks."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from app import integration_readiness as integration

def user():
    return SimpleNamespace(id=1)

def test_readiness_denies_non_admin(monkeypatch):
    monkeypatch.setattr(integration,"profile",lambda db,user:{"role":"Viewer","geographic_scope":"Nationwide","status":"Active","permissions":{"administration":False}})
    monkeypatch.setattr(integration,"has",lambda p,k:p["permissions"].get(k,False))
    with pytest.raises(HTTPException) as err:
        integration.require_admin(None,user())
    assert err.value.status_code==403

def test_readiness_denies_regional_admin(monkeypatch):
    monkeypatch.setattr(integration,"profile",lambda db,user:{"role":"Provincial Administrator","geographic_scope":"Province","status":"Active","permissions":{"administration":True}})
    monkeypatch.setattr(integration,"has",lambda p,k:p["permissions"].get(k,False))
    with pytest.raises(HTTPException) as err:
        integration.require_admin(None,user())
    assert err.value.status_code==403

def test_readiness_returns_only_aggregate_counts(monkeypatch):
    monkeypatch.setattr(integration,"require_admin",lambda db,user:None)
    engine=create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE social_listening_results(id INTEGER PRIMARY KEY,canonical_url TEXT,platform TEXT,published_at TEXT,text_content TEXT,observed_handle TEXT,author_name TEXT,provider_result_id TEXT,promoted_intelligence_id INTEGER)"))
        conn.execute(text("CREATE TABLE intelligence_items(id INTEGER PRIMARY KEY,source_id TEXT,source_url TEXT,platform TEXT,original_content TEXT)"))
        conn.execute(text("CREATE TABLE watchlist_items(id INTEGER PRIMARY KEY,type TEXT,status TEXT)"))
        conn.execute(text("INSERT INTO social_listening_results VALUES (8,'https://example.org/post','x','','sample','@test','','',42)"))
        conn.execute(text("INSERT INTO intelligence_items VALUES (42,'','','x','sample')"))
        conn.execute(text("INSERT INTO watchlist_items VALUES (7,'Candidate','Active')"))
    with Session(engine) as db:
        result=integration.readiness(user(),db)
    assert result["social_posts"]["total"]==1
    assert result["social_posts"]["missing_publication"]==1
    assert result["promotion_lineage"]["eligible_backfill"]==1
    assert result["promotion_lineage"]["conflicts"]==0
    assert result["candidates"]["active"]==1
    assert result["intelligence_provenance"]["missing_url"]==1
    assert result["platform_quality"][0]["missing_publication"]==1
    assert result["platform_quality"][0]["missing_provider_id"]==1
    assert "https://example.org/post" not in str(result)
    assert result["release_gates"]["source_id_backfill_needed"] is True
    assert result["release_gates"]["promoted_source_id_integrity"] is False
    assert result["release_gates"]["social_source_provenance_complete"] is False
    assert result["release_gates"]["manual_validation_required"] is True
    assert result["paid_requests"]==0
    engine.dispose()

def test_backfill_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(integration,"require_admin",lambda db,user:None)
    with pytest.raises(HTTPException) as err:
        integration.apply_backfill(integration.BackfillRequest(confirm=False,expected_missing=1),user(),None)
    assert err.value.status_code==409

def test_backfill_is_denied_before_database_access(monkeypatch):
    monkeypatch.setattr(integration,"require_admin",lambda db,user:(_ for _ in ()).throw(HTTPException(403,"Denied")))
    with pytest.raises(HTTPException) as err:
        integration.preview_backfill(user(),None)
    assert err.value.status_code==403

def test_provenance_review_queue_admin_only(monkeypatch):
    monkeypatch.setattr(integration,"require_admin",lambda db,user:(_ for _ in ()).throw(HTTPException(403,"Denied")))
    with pytest.raises(HTTPException) as err:
        integration.provenance_review_queue(100,0,user(),None)
    assert err.value.status_code==403

def test_provenance_review_queue_redacts_content_and_urls(monkeypatch):
    monkeypatch.setattr(integration,"require_admin",lambda db,user:None)
    engine=create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE social_listening_results(id INTEGER PRIMARY KEY,platform TEXT,canonical_url TEXT,published_at TEXT,provider_result_id TEXT,text_content TEXT,observed_handle TEXT,author_name TEXT)"))
        conn.execute(text("INSERT INTO social_listening_results VALUES (101,'threads','https://example.org/private','','','sensitive original post','@public','')"))
    with Session(engine) as db:
        result=integration.provenance_review_queue(100,0,user(),db)
    assert len(result["results"])==1
    assert result["results"][0]["source_id"]=="social:101"
    assert result["results"][0]["missing_fields"]==["publication_time","provider_record_id"]
    assert "sensitive original post" not in str(result)
    assert "https://example.org/private" not in str(result)
    engine.dispose()
