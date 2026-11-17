"""Citation coverage is not factual or legal accuracy."""
import pytest
from fastapi import HTTPException
from app import assistant_saved_history_eval as replay
from test_saved_reply_eval_v1616 import session,req

@pytest.mark.parametrize("cards,answer,expected",[
    ([{"id":"SOCIAL-7"}],"No displayed citation label.","SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS"),
    ([{"id":"SOCIAL-7"}],"Cites another post [SOCIAL-8].","DISPLAYED_CITATIONS_MISSING_FROM_SAVED_CARDS"),
    ([], "Cites one post [SOCIAL-7].","DISPLAYED_CITATIONS_WITHOUT_SAVED_CARDS"),
    ([{"id":"SOCIAL-7"}],"Cites saved post [SOCIAL-7].","DISPLAYED_CITATIONS_WITH_SAVED_CARDS"),
])
def test_format_diagnostic(cards,answer,expected):
    scope=replay._reply_scope([
        {"role":"user","text":"Review saved public evidence"},
        {"role":"assistant","text":answer,"records":cards}],1)
    assert scope["eligible"]
    assert replay._historical_citation_coverage(scope)==expected

def test_batch_coverage_is_not_accuracy(session,monkeypatch):
    row=session.query(replay.AssistantThread).filter_by(user_id=3).first()
    row.messages_json='[{"role":"user","text":"Review one public post"},{"role":"assistant","text":"No displayed citation here.","records":[{"id":"SOCIAL-7"}]}]'
    session.commit()
    monkeypatch.setattr(replay,"resolve_mixed_audit_sources",lambda *args:[
        {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","source_excerpt":"Public post"}])
    result=replay.audit_owned_saved_reply_batch(session,{},3,[req()])
    assert result["citation_coverage_counts"]=={"SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS":1}
    assert result["source_unavailable_review_count"]==0
    assert result["citation_coverage_is_format_diagnostic_only"] is True
    assert result["human_accuracy"] is None and result["human_verified_errors"]==0

def test_unavailable_not_attribution_failure(session,monkeypatch):
    def unavailable(*args):
        raise HTTPException(404,"Source not authorized")
    monkeypatch.setattr(replay,"resolve_mixed_audit_sources",unavailable)
    result=replay.audit_owned_saved_reply_batch(session,{},3,[req()])
    assert result["source_unavailable_review_count"]==1
    assert result["citation_coverage_counts"]=={}
    assert result["human_accuracy"] is None
