"""Historical replay: citations outside the saved card shortlist get reauthorized."""
import pytest
from fastapi import HTTPException,Response
from app import assistant_saved_history_eval as h
from test_saved_reply_eval_v1616 import session,current,req

def thread_messages(cards,answer="Source [SOCIAL-7] and related [SOCIAL-8]."):
    return [{"role":"user","text":"Compare saved evidence"},
            {"role":"assistant","text":answer,"records":cards}]

def test_cited_id_omitted_from_cards_is_added_to_exact_reauthorization_scope():
    data=h._reply_scope(thread_messages([{"id":"SOCIAL-7"}]),1)
    assert data["eligible"]
    assert data["source_ids"]==["SOCIAL-7","SOCIAL-8"]
    assert data["cited_only_source_count"]==1
    assert data["replay_scope"]=="SAVED_CARDS_PLUS_EXPLICIT_CITATIONS"

def test_same_id_in_card_and_prose_not_retrieved_twice():
    data=h._reply_scope(thread_messages([{"id":"SOCIAL-7"},{"id":"SOCIAL-8"}]),1)
    assert data["source_ids"]==["SOCIAL-7","SOCIAL-8"]
    assert data["cited_only_source_count"]==0

def test_legacy_numeric_card_id_does_not_override_formal_intelligence_id():
    data=h._reply_scope(thread_messages(
        [{"id":1,"intelligence_id":"INT-2026-000001","evidence_type":"OBSERVED"}],
        "Inbox review [INT-2026-000001]."),1)
    assert data["source_ids"]==["INT-2026-000001"]

def test_citation_only_reply_requires_source_reauthorization():
    data=h._reply_scope(thread_messages([],"Public source [SOCIAL-7]."),1)
    assert data["eligible"]
    assert data["source_ids"]==["SOCIAL-7"]
    assert data["cited_only_source_count"]==1

def test_empty_cards_and_no_citations_remain_ineligible():
    data=h._reply_scope(thread_messages([],"Summary with no citations."),1)
    assert not data["eligible"]
    assert data["reason_code"]=="NO_SAVED_EVIDENCE_CARDS_OR_CITATIONS"

def test_malformed_cited_reference_fails_closed():
    data=h._reply_scope(thread_messages([{"id":"SOCIAL-7"}],
        "Citation [SOCIAL-0] is invalid."),1)
    assert not data["eligible"]
    assert data["reason_code"]=="INVALID_DISPLAYED_SOURCE_REFERENCE"

@pytest.mark.parametrize("count", [13,16,19,20])
def test_combined_card_and_citation_scope_safely_supports_historical_sizes(count):
    cards=[{"id":f"SOCIAL-{i}"} for i in range(1,13)]
    answer="Evidence "+" ".join(f"[SOCIAL-{i}]" for i in range(13,count+1))
    data=h._reply_scope(thread_messages(cards,answer),1)
    assert data["eligible"]
    assert len(data["source_ids"])==count
    assert data["cited_only_source_count"]==count-12

def test_more_than_twenty_distinct_ids_is_ineligible_not_truncated():
    cards=[{"id":f"SOCIAL-{i}"} for i in range(1,13)]
    answer="Evidence "+" ".join(f"[SOCIAL-{i}]" for i in range(13,22))
    data=h._reply_scope(thread_messages(cards,answer),1)
    assert not data["eligible"]
    assert data["reason_code"]=="COMBINED_SOURCE_SCOPE_EXCEEDS_LIMIT"
    assert data["source_ids"]==[]

def test_invalid_cited_id_not_checked_as_a_different_record(session,monkeypatch):
    obj=session.query(h.AssistantThread).filter_by(user_id=3).first()
    obj.messages_json='[{"role":"user","text":"Compare saved posts"},{"role":"assistant","text":"Public sources [SOCIAL-7] [SOCIAL-8].","records":[{"id":"SOCIAL-7"}]}]'
    session.commit()
    seen=[]
    def authorize(db,p,request):
        seen.append(list(request.source_ids))
        raise HTTPException(404,"Source not accessible in the current scope")
    monkeypatch.setattr(h,"resolve_mixed_audit_sources",authorize)
    with pytest.raises(HTTPException) as e:
        h.saved_reply_audit(req(),Response(),current(),session)
    assert e.value.status_code==404
    assert seen==[["SOCIAL-7","SOCIAL-8"]]

def test_batch_missing_cited_source_fails_not_fake_pass(session,monkeypatch):
    obj=session.query(h.AssistantThread).filter_by(user_id=3).first()
    obj.messages_json='[{"role":"user","text":"Compare saved posts"},{"role":"assistant","text":"Public sources [SOCIAL-7] [SOCIAL-8].","records":[{"id":"SOCIAL-7"}]}]'
    session.commit()
    monkeypatch.setattr(h,"resolve_mixed_audit_sources",
        lambda db,p,request: (_ for _ in ()).throw(HTTPException(404,"Hidden evidence")))
    result=h.audit_owned_saved_reply_batch(session,{"status":"Active"},3,[req()])
    assert result["audited"]==0
    assert result["unavailable_source"]==1
    assert result["human_accuracy"] is None

def test_20_reference_request_is_accepted_but_has_no_automatic_authority():
    from app.assistant_eval_sampling import MixedAnswerAuditRequest
    refs=[f"SOCIAL-{i}" for i in range(1,21)]
    data=MixedAnswerAuditRequest(source_ids=refs,
        question="Which posts are relevant?",answer="Unverified [SOCIAL-1].")
    assert len(data.source_ids)==20
    assert data.source_ids[0]=="SOCIAL-1"
