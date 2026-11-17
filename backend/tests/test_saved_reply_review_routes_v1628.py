"""Deterministic review-routing labels never confer accuracy or permission."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_saved_history_eval as replay
from test_saved_reply_eval_v1616 import session,current,req

@pytest.mark.parametrize("status,coverage,count,route",[
    ("SOURCE_UNAVAILABLE",None,0,"RECHECK_CURRENT_EVIDENCE_ACCESS"),
    ("UNAVAILABLE",None,0,"VERIFY_OWNED_HISTORY_SELECTION"),
    ("INELIGIBLE",None,0,"INSPECT_HISTORY_FORMAT_MANUALLY"),
    ("AUDITED","SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS",0,"REVIEW_CITATION_ATTRIBUTION"),
    ("AUDITED","DISPLAYED_CITATIONS_MISSING_FROM_SAVED_CARDS",2,"REVIEW_CITATION_ATTRIBUTION"),
    ("AUDITED","DISPLAYED_CITATIONS_WITH_SAVED_CARDS",1,"REVIEW_FLAGGED_CLAIMS_WITH_SOURCES"),
    ("AUDITED","DISPLAYED_CITATIONS_WITH_SAVED_CARDS",0,"HUMAN_EVIDENCE_SPOT_CHECK"),
])
def test_review_route_is_deterministic(status,coverage,count,route):
    assert replay._historical_review_route(status,coverage,count)==route

def test_single_replay_has_nonverdict_route(session,monkeypatch):
    monkeypatch.setattr(replay,"resolve_mixed_audit_sources",lambda *args:[
      {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","source_excerpt":"Post"}])
    result=replay.saved_reply_audit(req(),Response(),current(),session)
    assert result["review_route"] in (
       "REVIEW_CITATION_ATTRIBUTION","REVIEW_FLAGGED_CLAIMS_WITH_SOURCES",
       "HUMAN_EVIDENCE_SPOT_CHECK")
    assert result["review_route_is_suggestion_only"] is True
    assert result["human_accuracy"] is None and result["factual_accuracy_verified"] is False

def test_batch_unavailable_source_has_no_accuracy_score(session,monkeypatch):
    def unavailable(*args): raise HTTPException(404,"No authorized source")
    monkeypatch.setattr(replay,"resolve_mixed_audit_sources",unavailable)
    result=replay.audit_owned_saved_reply_batch(session,{},3,[req()])
    assert result["review_route_counts"]=={"RECHECK_CURRENT_EVIDENCE_ACCESS":1}
    assert result["results"][0]["review_route"]=="RECHECK_CURRENT_EVIDENCE_ACCESS"
    assert result["human_accuracy"] is None and result["human_verified_errors"]==0
    assert result["review_routes_are_unverified_suggestions"] is True
