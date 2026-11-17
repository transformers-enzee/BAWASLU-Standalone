"""Regression from observed saved reply history: nine replies cited >12 distinct IDs."""
import pytest
from app.assistant_grounding import audit_assistant_answer
from app.assistant_eval_sampling import MixedAnswerAuditRequest,build_mixed_answer_audit
from app.assistant_saved_history_eval import _reply_scope

def evidence(count):
    return [{"record_id":f"SOCIAL-{i}","record_type":"SOCIAL_LISTENING",
             "source_excerpt":f"Observed example source {i}"} for i in range(1,count+1)]

def question_answer(count=19):
    return "Evaluate these sources", " ".join(
        f"Sample allegation [SOCIAL-{i}]." for i in range(1,count+1))

@pytest.mark.parametrize("count",[13,16,19,20])
def test_historical_audit_preserves_existing_authorized_refs(count):
    q,answer=question_answer(count)
    request=MixedAnswerAuditRequest(source_ids=[x["record_id"] for x in evidence(count)],
                                    question=q,answer=answer)
    result=build_mixed_answer_audit(evidence(count),request)
    assert len(result["cited_authorized_ids"])==count
    assert result["rejected_unavailable_citation_count"]==0
    assert result["audit_citation_reference_limit"]==20
    assert result["normal_assistant_citation_reference_limit"]==12
    assert result["human_accuracy"] is None
    assert result["raw_source_text_included"] is False
    assert "Observed example" not in str(result)
    assert "Sample allegation" not in str(result)

def test_normal_assistant_still_limits_display_to_twelve_citations():
    q,answer=question_answer(19)
    visible,cited,meta=audit_assistant_answer(q,evidence(19),answer,[],language="en")
    assert len(cited)==12
    assert meta["citation_reference_limit"]==12
    assert meta["omitted_excess_citation_count"]==7
    assert "[SOCIAL-19]" not in visible
    assert "[SOCIAL-12]" in visible

def test_read_only_citation_reconciliation_preserves_nineteen():
    q,answer=question_answer(19)
    visible,cited,meta=audit_assistant_answer(
        q,evidence(19),answer,[],language="en",citation_limit=20)
    assert len(cited)==19
    assert meta["citation_reference_limit"]==20
    assert meta["omitted_excess_citation_count"]==0
    assert "[SOCIAL-19]" in visible

def test_unavailable_historical_reference_is_not_accepted_even_with_wider_budget():
    q,answer=question_answer(19)
    visible,cited,meta=audit_assistant_answer(
        q,evidence(18),answer,[],language="en",citation_limit=20)
    assert len(cited)==18
    assert meta["rejected_unavailable_citations"]==1
    assert "[SOCIAL-19]" not in visible
    assert meta["source_truth_verified"] is False

def test_replay_union_and_wider_citation_budget_match():
    q,answer=question_answer(19)
    messages=[{"role":"user","text":q},
              {"role":"assistant","text":answer,
               "records":[{"id":f"SOCIAL-{i}"} for i in range(1,13)]}]
    scope=_reply_scope(messages,1)
    assert scope["eligible"] is True
    assert len(scope["source_ids"])==19
    assert scope["cited_only_source_count"]==7
    result=build_mixed_answer_audit(evidence(19),MixedAnswerAuditRequest(
        question=q,answer=answer,source_ids=scope["source_ids"]))
    assert len(result["cited_authorized_ids"])==19
    assert result["audit_citation_reference_limit"]==20

def test_citation_budget_never_expands_above_twenty():
    q,answer=question_answer(20)
    visible,cited,meta=audit_assistant_answer(
        q,evidence(20),answer,[],language="en",citation_limit=999)
    assert len(cited)==20
    assert meta["citation_reference_limit"]==20
    assert meta["legal_verdict_confirmed"] is False
