"""Bounded, ownership-restricted batch QA. All cases use isolated fixtures."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_saved_history_eval as module
from app.assistant_saved_history_eval import (
    SavedReplyAuditRequest,BatchSavedReplyAuditRequest,
    audit_owned_saved_reply_batch,saved_reply_batch_audit)
from test_saved_reply_eval_v1616 import session,current,req

def request(*items):
    return BatchSavedReplyAuditRequest(selections=[
        SavedReplyAuditRequest(thread_id=tid,answer_message_index=idx)
        for tid,idx in items])

OWNED="11111111-1111-4111-8111-111111111111"
OTHER="22222222-2222-4222-8222-222222222222"
MISSING="99999999-9999-4999-8999-999999999999"

def test_owned_batch_one_reply_source_auth_and_privacy(session,monkeypatch):
    def scoped(db,payload,request):
        return [{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                 "source_excerpt":"Current private post excerpt"}]
    monkeypatch.setattr(module,"resolve_mixed_audit_sources",scoped)
    response=Response()
    data=saved_reply_batch_audit(request((OWNED,1)),response,current(),session)
    assert data["audited"]==1
    assert data["requested"]==1
    assert data["human_accuracy"] is None
    assert data["human_verified_errors"]==0
    assert data["answers_generated"]==0 and data["database_writes"]==0
    assert data["results"][0]["source_record_ids"]==["SOCIAL-7"]
    assert data["results"][0]["status"]=="AUDITED"
    assert data["selection_not_random_or_representative"] is True
    assert response.headers["Cache-Control"]=="private, no-store"
    assert response.headers["X-Evaluation-Generation"]=="NONE"
    assert "Current private post excerpt" not in str(data)
    assert "One post raises a concern" not in str(data)

def test_other_user_thread_not_audited_or_disclosed(session,monkeypatch):
    called=[]
    def authorized_only(db,principal,selection):
        called.append(list(selection.source_ids))
        assert selection.source_ids==["SOCIAL-7"]
        return [{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                 "source_excerpt":"Authorized original source"}]
    monkeypatch.setattr(module,"resolve_mixed_audit_sources",authorized_only)
    data=saved_reply_batch_audit(
        request((OWNED,1),(OTHER,1)),Response(),current(),session)
    assert data["audited"]==1
    assert data["unavailable"]==1
    assert data["results"][1]["reason_code"]=="SAVED_CONVERSATION_UNAVAILABLE"
    assert "Other answer" not in str(data)
    assert called==[["SOCIAL-7"]]

def test_nonexistent_thread_has_same_denial_as_other_user(session):
    data=saved_reply_batch_audit(
        request((OTHER,1),(MISSING,1)),Response(),current(),session)
    assert [x["status"] for x in data["results"]]==["UNAVAILABLE","UNAVAILABLE"]
    assert data["unavailable"]==2

def test_stale_source_is_explicit_failure_not_success(session,monkeypatch):
    def reject(*a):
        raise HTTPException(404,"Invisible private record")
    monkeypatch.setattr(module,"resolve_mixed_audit_sources",reject)
    data=saved_reply_batch_audit(request((OWNED,1)),Response(),current(),session)
    assert data["audited"]==0
    assert data["unavailable_source"]==1
    assert data["results"][0]["status"]=="SOURCE_UNAVAILABLE"
    assert "Invisible private record" not in str(data)

def test_duplicate_batch_selection_fails_closed(session):
    with pytest.raises(HTTPException) as e:
        audit_owned_saved_reply_batch(
            session,{"status":"Active"},3,[req(),req()])
    assert e.value.status_code==422

def test_six_entries_rejected_before_database_access():
    with pytest.raises(Exception):
        BatchSavedReplyAuditRequest(selections=[req() for _ in range(6)])

def test_inactive_account_cannot_read_batch(session,monkeypatch):
    monkeypatch.setattr(module,"profile",
        lambda db,user:{"status":"Inactive","permissions":{"view_intelligence":True}})
    with pytest.raises(HTTPException) as e:
        saved_reply_batch_audit(request((OWNED,1)),Response(),current(),session)
    assert e.value.status_code==403

def test_no_real_answer_accuracy_result_for_clean_batch(session,monkeypatch):
    monkeypatch.setattr(module,"resolve_mixed_audit_sources",
        lambda *a:[{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                    "source_excerpt":"Authorized updated post"}])
    data=saved_reply_batch_audit(request((OWNED,1)),Response(),current(),session)
    assert data["human_accuracy"] is None
    assert data["real_model_generation_provenance_verified"] is False
    assert data["source_truth_verified"] is False
