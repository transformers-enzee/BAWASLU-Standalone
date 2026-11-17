"""Formal evidence: exact words, topical ranking, no status-based false match."""
from datetime import datetime,timezone
from types import SimpleNamespace
from app.assistant_evidence_relevance import formal_source_term_score,retrieval_scope_note
from app.intelligence_assistant import select_assistant_records
from app import intelligence_assistant as intel
import pytest

def _rec(id,title,body,**changes):
    values=dict(id=id,title=title,original_content=body,province="",regency_city="",
      platform="",author="",source_name="",priority="Medium",
      review_status="Pending Review",verification_status="UNVERIFIED",
      publication_date="2026-11-01",publication_datetime="",
      collection_datetime="",created_at=datetime(2026,11,1,tzinfo=timezone.utc),
      validated_at=None,source_id=f"social:{id}")
    values.update(changes)
    return SimpleNamespace(**values)

def test_exact_word_and_title_weight():
    assert formal_source_term_score(["riau"],"Keriau","")==0
    assert formal_source_term_score(["riau"],"Riau field report","")>0
    assert formal_source_term_score(["riau"],"Riau","")>formal_source_term_score(["riau"],"","Riau")
    assert formal_source_term_score(["riau"],"","",geography="Riau")>0
    assert formal_source_term_score(["gibran"],"","",approved={"candidate":"Gibran"})>0

def test_review_status_alone_is_not_evidence(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda x:{})
    rows=[_rec(1,"Administrative note","Routine correspondence",review_status="Riau",
        verification_status="Riau")]
    assert select_assistant_records("Riau",rows)==[]
    assert select_assistant_records("Riau",[_rec(2,"Riau field report","Incident note")])[0].id==2

def test_topical_relevance_precedes_recency(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda x:{})
    rows=[_rec(1,"Provincial update","Generic note from Riau",publication_date="2026-11-17"),
          _rec(2,"Riau report","Riau incident report",publication_date="2026-10-10")]
    assert [x.id for x in select_assistant_records("Riau",rows)]==[2,1]

def test_existing_validation_and_priority_filters_hold(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda x:{})
    rows=[_rec(1,"Riau report","Post",priority="Low",review_status="Pending Review"),
          _rec(2,"Riau report","Post",priority="High",
               review_status="Validated as Relevant Intelligence")]
    assert [x.id for x in select_assistant_records("highest priority validated Riau",rows)]==[2]

def test_selected_subset_is_not_all_posts():
    assert retrieval_scope_note("Question",0,0)==""
    s=retrieval_scope_note("Riau",3,8)
    for word in ("3 authorized Inbox","8 authorized Social Listening",
                 "NOT total campaign","exhaustive database search","concrete next check"):
        assert word in s

def test_helper_does_not_mutate_approved_values():
    approved={"candidate":"Gibran"}
    assert formal_source_term_score(["gibran"],"","",approved=approved)>0
    assert approved=={"candidate":"Gibran"}
