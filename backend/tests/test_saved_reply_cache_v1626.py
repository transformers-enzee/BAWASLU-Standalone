"""Request-local reuse never authorizes unavailable sources; uncited cards flagged."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_eval_sampling as sampling,assistant_saved_history_eval as replay,inbox_radar
from app.assistant_eval_sampling import MixedAnswerAuditRequest,resolve_mixed_audit_sources
from test_saved_reply_eval_v1616 import session,current,req

def source(n):
    return {"result_id":str(n),"canonical_source_id":f"social:{n}",
            "message_original":"Unverified monitored public post"}

def test_same_request_reuses_scoped_social_inventory(monkeypatch):
    reads=[]
    def get(db,principal):
        reads.append(1)
        return ([{"posts":[source(7),source(8)]}],{})
    monkeypatch.setattr(inbox_radar,"live_inbox_findings",get)
    principal={"_assistant_eval_batch_cache":{}}
    for n in (7,8):
        r=MixedAnswerAuditRequest(source_ids=[f"SOCIAL-{n}"],
          question="Review public evidence",answer=f"Public post [SOCIAL-{n}]")
        found=resolve_mixed_audit_sources(None,principal,r)
        assert found[0]["record_id"]==f"SOCIAL-{n}"
    assert len(reads)==1
    assert "scoped_findings" in principal["_assistant_eval_batch_cache"]
    resolve_mixed_audit_sources(None,{},r)
    assert len(reads)==2

def test_cached_scope_cannot_authorize_hidden_source(monkeypatch):
    monkeypatch.setattr(inbox_radar,"live_inbox_findings",
      lambda db,p:([{"posts":[source(7)]}],{}))
    p={"_assistant_eval_batch_cache":{}}
    good=MixedAnswerAuditRequest(source_ids=["SOCIAL-7"],question="Review evidence",
      answer="Post [SOCIAL-7]")
    resolve_mixed_audit_sources(None,p,good)
    with pytest.raises(HTTPException) as e:
        resolve_mixed_audit_sources(None,p,MixedAnswerAuditRequest(
          source_ids=["SOCIAL-999"],question="Review evidence",answer="Post [SOCIAL-999]"))
    assert e.value.status_code==404

def test_single_replay_no_citations_has_explicit_diagnostic(session,monkeypatch):
    row=session.query(replay.AssistantThread).filter_by(user_id=3).first()
    row.messages_json='[{"role":"user","text":"Summarize public post"},{"role":"assistant","text":"A summary with no citation labels.","records":[{"id":"SOCIAL-7"}]}]'
    session.commit()
    monkeypatch.setattr(replay,"resolve_mixed_audit_sources",lambda *a:[
      {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","source_excerpt":"Public post"}])
    result=replay.saved_reply_audit(req(),Response(),current(),session)
    assert result["historical_citation_coverage"]=="SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS"
    assert result["human_accuracy"] is None

def test_batch_no_citations_is_counted_not_scored(session,monkeypatch):
    row=session.query(replay.AssistantThread).filter_by(user_id=3).first()
    row.messages_json='[{"role":"user","text":"Summarize public post"},{"role":"assistant","text":"A summary with no citation labels.","records":[{"id":"SOCIAL-7"}]}]'
    session.commit()
    monkeypatch.setattr(replay,"resolve_mixed_audit_sources",lambda *a:[
      {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","source_excerpt":"Public post"}])
    result=replay.audit_owned_saved_reply_batch(session,{},3,[req()])
    assert result["saved_cards_without_displayed_citations"]==1
    assert result["batch_scoped_evidence_cache_only"] is True
    assert result["audited"]==1 and result["human_accuracy"] is None
