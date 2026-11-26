"""v184.8: Governance ledger reconciliation and independent human-gate QA."""
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.governance_projection import source_snapshot_fingerprint
from app.governance_integration import inbox_governance_annotations
from app.governance_persistence import governance_review_queue, governance_readiness, decide_insight

def row(**kw):
    return SimpleNamespace(**kw)

def test_existing_officer_review_changes_source_fingerprint():
    source=row(id=3,text_content="election candidate",canonical_url="https://example.test/a")
    assessment=row(id=8,assessment_version=2,relevance_label="RELEVANT",sentiment="NEUTRAL")
    a=source_snapshot_fingerprint(source,assessment,[],{"officer_sentiment":None,"evidence_review":None})
    b=source_snapshot_fingerprint(source,assessment,[],{
        "officer_sentiment":row(id=40,sentiment="NEGATIVE"),"evidence_review":None})
    c=source_snapshot_fingerprint(source,assessment,[],{
        "officer_sentiment":row(id=40,sentiment="NEGATIVE"),
        "evidence_review":row(id=41,decision="FLAG_DISMISSED")})
    assert len({a,b,c})==3

def test_review_ledger_conflict_detected_without_display_override(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED","true")
    db=MagicMock()
    gov=row(id=1,campaign_id=2,result_id=4,field="sentiment",status="approved",
            human_value="NEGATIVE",revision=1,reviewer_id=3)
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value=[gov]
    records=[{"id":"4","campaign_id":"2","assessment_version":1,
              "model_version":"m","sentiment":"POSITIVE","ai_sentiment_original":"NEUTRAL",
              "relevance_label":"RELEVANT","sentiment_correction":{"sentiment":"POSITIVE"}}]
    overlay=inbox_governance_annotations(db,records)[(2,4)]
    assert overlay["fields"]["sentiment"]["ai_value"]=="NEUTRAL"
    assert overlay["fields"]["sentiment"]["effective_value"]=="NEGATIVE"
    assert overlay["officer_ledgers_conflict"] is True
    assert overlay["legacy_display_remains_authoritative"] is True
    assert records[0]["sentiment"]=="POSITIVE"

def test_equal_legacy_and_governance_sentiment_no_conflict(monkeypatch):
    monkeypatch.setenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED","true")
    db=MagicMock()
    gov=row(id=2,campaign_id=1,result_id=1,field="sentiment",status="approved",
            human_value="NEGATIVE",revision=1,reviewer_id=6)
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value=[gov]
    overlay=inbox_governance_annotations(db,[{
        "campaign_id":"1","id":"1","ai_sentiment_original":"NEUTRAL",
        "relevance_label":"RELEVANT",
        "sentiment_correction":{"sentiment":"NEGATIVE"}
    }])[(1,1)]
    assert not overlay["requires_resolution"]

def test_unapproved_insight_cannot_be_self_approved():
    # Statically verify separation of proposal and independent approval at write boundary.
    body=inspect.getsource(decide_insight)
    assert 'row.proposer_id==user.id and body.decision=="approve"' in body
    assert 'HTTPException(403' in body
    assert 'insight_publication_gate' in body

def test_review_queue_opt_in_disabled(monkeypatch):
    monkeypatch.delenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED",raising=False)
    with pytest.raises(HTTPException) as exc:
        governance_review_queue(campaign_id=1,limit=5,user=row(id=1),db=MagicMock())
    assert exc.value.status_code==503

def test_readiness_does_not_enable_writes():
    src=inspect.getsource(governance_readiness)
    assert 'inspect(bind)' in src
    assert 'ready_for_controlled_staging_qa' in src
    assert 'db.commit(' not in src
