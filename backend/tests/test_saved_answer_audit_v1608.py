"""Real saved-source read-only QA, with isolated authorized Inbox fixtures."""
import json
import pytest
from fastapi import HTTPException,Response
from app.assistant_eval_sampling import (
    SavedAnswerAuditRequest,build_saved_answer_audit,saved_answer_audit)
from app.models import User
from test_management_briefings_v1468 import dataset

def post(number,body="Riau oversight questions from an unverified public post",
         sentiment="NEGATIVE"):
    return {"result_id":str(number),"canonical_source_id":f"social:{number}",
            "message_original":body,"sentiment":sentiment,
            "source_url":f"https://example.invalid/{number}"}

def findings():
    return [{"kind":"discussion","posts":[post(7),post(9)]}]

def payload(ids=None,answer="A post discusses Riau [SOCIAL-7]."):
    return SavedAnswerAuditRequest(source_ids=ids or ["SOCIAL-7"],
        question="What does the saved Riau post say?",answer=answer)

def test_authorized_post_is_audited_without_returning_raw_text_or_answer():
    x=build_saved_answer_audit(findings(),payload())
    assert x["source_record_ids"]==["SOCIAL-7"]
    assert x["cited_authorized_ids"]==["SOCIAL-7"]
    assert x["source_count"]==1 and x["cited_count"]==1
    assert x["human_accuracy"] is None
    assert x["claimed_answer_is_original_model_output_verified"] is False
    assert x["pasted_answer_stored"] is False and x["database_writes"]==0
    assert x["paid_ai_calls"]==0 and not x["source_truth_verified"]
    encoded=json.dumps(x)
    assert "Riau oversight questions from an unverified" not in encoded
    assert "A post discusses Riau" not in encoded

def test_forged_citation_is_not_accepted_as_selected_evidence():
    x=build_saved_answer_audit(findings(),payload(
        answer="Unsupported claim [SOCIAL-999]."))
    assert x["cited_authorized_ids"]==[]
    assert x["rejected_unavailable_citation_count"]==1

@pytest.mark.parametrize("source_ids",[
    ["SOCIAL-7","SOCIAL-999"],["SOCIAL-0"],["SOCIAL-07"],
    ["SOCIAL-7","SOCIAL-7"],["INT-7"],["SOCIAL-abc"]
])
def test_all_or_nothing_source_scope_does_not_enumerate_hidden_rows(source_ids):
    req=payload(ids=source_ids)
    with pytest.raises(HTTPException) as ex:
        build_saved_answer_audit(findings(),req)
    assert ex.value.status_code in (404,422)

def test_multiple_sources_deduplicate_cross_campaign_links():
    rows=findings()+[{"kind":"source_awareness","posts":[post(7)]}]
    x=build_saved_answer_audit(rows,payload(
        ids=["SOCIAL-7","SOCIAL-9"],
        answer="Riau context [SOCIAL-7]. Another source [SOCIAL-9]."))
    assert x["source_count"]==2
    assert x["cited_count"]==2

def test_empty_original_text_is_not_accepted_as_evidence():
    with pytest.raises(HTTPException) as e:
        build_saved_answer_audit([{"posts":[post(7,body=" ")]}],payload())
    assert e.value.status_code==404

def test_conflicting_versions_require_manual_source_review():
    rows=[{"posts":[post(7)]},{"posts":[post(7,sentiment="POSITIVE")]}]
    with pytest.raises(HTTPException) as e:
        build_saved_answer_audit(rows,payload())
    assert e.value.status_code==409

def test_real_source_endpoint_denies_unpermitted(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
                            lambda conn,p:(findings(),{}))
        monkeypatch.setattr(assistant_eval_sampling,"profile",
            lambda conn,user:{"status":"Active",
                "permissions":{"view_intelligence":False}})
        with pytest.raises(HTTPException) as ex:
            saved_answer_audit(payload(),Response(),db.get(User,2),db)
        assert ex.value.status_code==403
    finally:db.close()

def test_endpoint_no_store_no_generation_and_authorized_scope(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
                            lambda conn,p:(findings(),{}))
        monkeypatch.setattr(assistant_eval_sampling,"profile",
            lambda conn,user:{"status":"Active",
                "permissions":{"view_intelligence":True},"province":"Riau"})
        response=Response()
        result=saved_answer_audit(payload(),response,db.get(User,2),db)
        assert result["source_count"]==1
        assert response.headers["Cache-Control"]=="private, no-store"
        assert response.headers["X-Evaluation-Generation"]=="NONE"
        assert response.headers["X-Acceptance-Status"]=="PENDING_HUMAN_REVIEW"
    finally:db.close()
