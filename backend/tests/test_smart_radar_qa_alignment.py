"""Analyst reference alignment protects original labels and repeated sources."""
import pytest
from fastapi import HTTPException
from app.smart_radar_qa_alignment import (
    blocked_references_from_rows,AnalystDecision,save_alignment_decision
)

def record(qid,url,decision=None,relation=None,rows=2):
    return {"qa_id":qid,"source_url":url,"source_rows":rows,
            "decision":decision,"source_relation":relation}

def test_group_cannot_be_used_with_only_one_comment_confirmed():
    rows=[record("QA-1","https://example.com/p", "confirmed","distinct_comments"),
          record("QA-2","https://example.com/p")]
    result=blocked_references_from_rows(rows)
    assert "QA-1" in result and "QA-2" in result

def test_distinct_comments_can_be_referenced_after_both_confirmed():
    rows=[record("QA-1","https://example.com/p", "confirmed","distinct_comments"),
          record("QA-2","https://example.com/p", "corrected","distinct_comments")]
    assert blocked_references_from_rows(rows)=={}

def test_same_underlying_content_is_not_allowed_as_independent_example():
    rows=[record("QA-1","https://example.com/p", "confirmed","same_underlying_content"),
          record("QA-2","https://example.com/p", "confirmed","distinct_comments")]
    assert len(blocked_references_from_rows(rows))==2

def test_needs_context_is_blocked():
    rows=[record("QA-1","https://example.com/1", "needs_context","not_applicable",1)]
    assert "QA-1" in blocked_references_from_rows(rows)

def test_reasoning_is_required_for_adjudication():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AnalystDecision(qa_id="QA-10649",decision="confirmed",
          approved_category="Election Operations",rationale="OK")

def test_original_category_cannot_be_corrected_to_same_value(monkeypatch):
    import app.smart_radar_qa_alignment as mod
    monkeypatch.setattr(mod,"reviewer",lambda db,user:{"name":"Signed in reviewer"})
    monkeypatch.setattr(mod,"queue_data",lambda db:[{"qa_id":"QA-10649"}])
    class Q:
        def mappings(self):return self
        def first(self):return {"qa_id":"QA-10649","source_url":"https://example.org/1",
              "category":"Election Operations","source_rows":1}
    class DB:
        def execute(self,*args,**kwargs):return Q()
    with pytest.raises(HTTPException) as exc:
        save_alignment_decision(AnalystDecision(qa_id="QA-10649",
          decision="corrected",approved_category="Election Operations",
          rationale="We have carefully checked the original post context.",
          source_relation="not_applicable"),
          user=type("U",(),{"id":12})(),db=DB())
    assert exc.value.status_code==422
