"""SQLite-backed authorization tests for offline scoring of saved Assistant replies.

No network, model invocations, external database, or officer-record mutations.
"""
import json
import pytest
from fastapi import HTTPException, Response
from app import assistant_saved_history_eval as module
from app.assistant_saved_history_eval import (
    SavedReplyHumanReviewRequest, SavedReplyAuditRequest,
    SavedReplyReviewerRating, saved_reply_human_review,
)
from app.assistant_saved_reply_human_packet import DIMENSIONS
from test_saved_reply_eval_v1616 import session,current

OWNED="11111111-1111-4111-8111-111111111111"
OTHER="22222222-2222-4222-8222-222222222222"


def _request(thread=OWNED, index=1, submit=True, ratings=None, **flags):
    submissions=[]
    if submit:
        submissions=[SavedReplyReviewerRating(
            thread_id=thread,answer_message_index=index,
            ratings=ratings or {x:"PASS" for x in DIMENSIONS},
            original_answer_reviewed=flags.get("original_answer_reviewed",True),
            independent_review_attested=flags.get("independent_review_attested",True))]
    return SavedReplyHumanReviewRequest(
        selections=[SavedReplyAuditRequest(
            thread_id=thread,answer_message_index=index)],
        submissions=submissions)


def _access(monkeypatch, admin=True):
    monkeypatch.setattr(module,"profile",lambda db,user:{
        "status":"Active",
        "permissions":{"view_intelligence":True,
                       "administration":admin}})


def _sources(monkeypatch):
    seen=[]
    def scoped(db,principal,request):
        seen.append(request.source_ids)
        return [{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
                 "source_excerpt":"PRIVATE LIVE AUTHORIZED SOURCE TEXT"}]
    monkeypatch.setattr(module,"resolve_mixed_audit_sources",scoped)
    return seen


def test_admin_reviews_owned_history_after_fresh_source_check(session,monkeypatch):
    _access(monkeypatch)
    seen=_sources(monkeypatch)
    response=Response()
    data=saved_reply_human_review(_request(),response,current(),session)
    assert seen==[["SOCIAL-7"]]
    assert data["scores"]["complete_self_attested_reviews"]==1
    assert data["scores"]["review_disposition_counts"][
        "HUMAN_REPORTED_ALL_DIMENSIONS_PASS"]==1
    assert data["source_access_reauthorized_during_request"] is True
    assert data["scores"]["formal_legal_signoff"] is False
    assert data["actual_model_accuracy"] is None
    assert data["review_data_persisted"] is False
    assert data["database_writes"]==0 and data["model_calls"]==0
    assert "PRIVATE LIVE AUTHORIZED SOURCE TEXT" not in json.dumps(data)
    assert "One post raises a concern" not in json.dumps(data)
    assert response.headers["Cache-Control"]=="private, no-store"
    assert response.headers["X-Evaluation-Generation"]=="NONE"


def test_admin_review_without_rating_is_not_review_completed(session,monkeypatch):
    _access(monkeypatch)
    _sources(monkeypatch)
    data=saved_reply_human_review(_request(submit=False),
                                  Response(),current(),session)
    assert data["scores"]["complete_self_attested_reviews"]==0
    assert data["scores"]["review_disposition_counts"]["NOT_SUBMITTED"]==1


def test_not_attested_review_remains_incomplete(session,monkeypatch):
    _access(monkeypatch)
    _sources(monkeypatch)
    data=saved_reply_human_review(
        _request(independent_review_attested=False),
        Response(),current(),session)
    assert data["scores"]["complete_self_attested_reviews"]==0
    assert data["scores"]["review_disposition_counts"]["INCOMPLETE_REVIEW"]==1


def test_non_admin_officer_cannot_score_historical_replies(session,monkeypatch):
    _access(monkeypatch,admin=False)
    seen=_sources(monkeypatch)
    with pytest.raises(HTTPException) as error:
        saved_reply_human_review(_request(),Response(),current(),session)
    assert error.value.status_code==403
    assert not seen


def test_other_user_history_stays_unavailable_before_scoring(session,monkeypatch):
    _access(monkeypatch)
    seen=_sources(monkeypatch)
    with pytest.raises(HTTPException) as error:
        saved_reply_human_review(_request(thread=OTHER),
                                 Response(),current(),session)
    assert error.value.status_code==422
    assert not seen


def test_current_source_denial_does_not_complete_review(session,monkeypatch):
    _access(monkeypatch)
    def denied(*args):
        raise HTTPException(404,"Secret hidden source")
    monkeypatch.setattr(module,"resolve_mixed_audit_sources",denied)
    with pytest.raises(HTTPException) as error:
        saved_reply_human_review(_request(),Response(),current(),session)
    assert error.value.status_code==422
    assert "Secret hidden source" not in str(error.value.detail)


def test_invalid_scoring_selection_is_rejected(session,monkeypatch):
    _access(monkeypatch)
    _sources(monkeypatch)
    request=_request()
    request.submissions[0].answer_message_index=2
    with pytest.raises(HTTPException) as error:
        saved_reply_human_review(request,Response(),current(),session)
    assert error.value.status_code==422


def test_unauthorized_answer_text_and_evidence_input_are_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SavedReplyHumanReviewRequest.model_validate({
            "selections":[{"thread_id":OWNED,"answer_message_index":1}],
            "submissions":[],
            "source_excerpt":"Forged source"})
    with pytest.raises(ValidationError):
        SavedReplyReviewerRating.model_validate({
            "thread_id":OWNED,"answer_message_index":1,
            "ratings":{"SOURCE_ID_ACCURACY":"PASS"},
            "answer_text":"Forged answer"})
