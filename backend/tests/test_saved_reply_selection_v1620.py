"""Selected-reply batch status reporting remains access-safe and nonrepresentative."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_saved_history_eval as service
from app.assistant_saved_history_eval import audit_owned_saved_reply_batch
from test_saved_reply_eval_v1616 import session,current
from test_saved_reply_batch_v1618 import request,OWNED,OTHER,MISSING

def test_explicit_selection_status_totals_and_denied_reasons(session,monkeypatch):
    def authorized(db,principal,selection):
        assert selection.source_ids==["SOCIAL-7"]
        return [{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                 "source_excerpt":"Authorized monitored source"}]
    monkeypatch.setattr(service,"resolve_mixed_audit_sources",authorized)
    result=audit_owned_saved_reply_batch(
        session,{"status":"Active","permissions":{"view_intelligence":True}},3,
        request((OWNED,1),(OTHER,1),(MISSING,1)).selections)
    assert result["selection_method"]=="EXPLICIT_USER_SELECTED_REPLIES"
    assert result["selected_reply_count"]==3
    assert result["audited"]==1
    assert result["unavailable"]==2
    assert result["reason_code_counts"]=={"SAVED_CONVERSATION_UNAVAILABLE":2}
    assert result["batch_is_representative"] is False
    assert result["human_accuracy"] is None
    assert result["human_verified_errors"]==0
    assert "Authorized monitored source" not in str(result)

def test_source_denial_distinguished_without_disclosing_hidden_source(session,monkeypatch):
    def denied(*args):
        raise HTTPException(403,"Hidden source and jurisdiction details")
    monkeypatch.setattr(service,"resolve_mixed_audit_sources",denied)
    result=audit_owned_saved_reply_batch(
        session,{"status":"Active","permissions":{"view_intelligence":True}},3,
        request((OWNED,1),(OTHER,1)).selections)
    assert result["audited"]==0
    assert result["reason_code_counts"]=={
      "CURRENT_SOURCE_ACCESS_OR_PRESENCE":1,"SAVED_CONVERSATION_UNAVAILABLE":1}
    assert result["unavailable_source"]==1
    assert "Hidden source" not in str(result)

def test_ineligible_selected_turn_is_counted_without_evidence_lookup(session,monkeypatch):
    called=[]
    monkeypatch.setattr(service,"resolve_mixed_audit_sources",
                        lambda *args:called.append(args))
    result=audit_owned_saved_reply_batch(
        session,{"status":"Active","permissions":{"view_intelligence":True}},3,
        request((OWNED,0)).selections)
    assert result["ineligible"]==1
    assert result["reason_code_counts"]=={"INVALID_ANSWER_TURN":1}
    assert not called
