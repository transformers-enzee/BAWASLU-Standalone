"""Exact Inbox-ID comparisons fail closed; tokenization respects place punctuation."""
from datetime import datetime,timezone
from types import SimpleNamespace
import pytest
from app.assistant_evidence_relevance import (
    exact_formal_source_ids,exact_formal_selection_complete,formal_source_term_score)
from app.intelligence_assistant import select_assistant_records
from app import intelligence_assistant as intel

def record(id,title="Riau monitoring",body="Observed report",**kwargs):
    r=dict(id=int(id[-6:]),intelligence_id=id,title=title,original_content=body,
      province="Riau",regency_city="",platform="Instagram",author="",source_name="",
      review_status="Pending Review",verification_status="UNVERIFIED",
      priority="Medium",publication_date="2026-11-01",publication_datetime="",
      collection_datetime="",created_at=datetime(2026,11,1,tzinfo=timezone.utc),
      validated_at=None,source_id="social:7")
    r.update(kwargs)
    return SimpleNamespace(**r)

def test_explicit_id_detection_is_bounded_and_exact():
    assert exact_formal_source_ids("Compare [INT-2026-000007] with INT-2026-000009")=={
        "INT-2026-000007","INT-2026-000009"}
    assert exact_formal_source_ids("INT-2026-000007extra, INT-2026-000007-A")==set()
    assert exact_formal_source_ids("INT-2026-000007") == {"INT-2026-000007"}

def test_requested_ids_override_topical_tokens(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda _: {})
    rows=[record("INT-2026-000007",title="Old monitoring"),
          record("INT-2026-000009",title="New monitoring"),
          record("INT-2026-000011",title="Unrelated")]
    q="Compare [INT-2026-000007] and [INT-2026-000009] regarding source evidence"
    ids={x.intelligence_id for x in select_assistant_records(q,rows)}
    assert ids=={"INT-2026-000007","INT-2026-000009"}
    assert exact_formal_selection_complete(q,rows[:2])

def test_missing_explicit_id_prevents_substitutions(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda _: {})
    rows=[record("INT-2026-000007"),record("INT-2026-000011")]
    q="Compare INT-2026-000007 to INT-2026-000009"
    assert select_assistant_records(q,rows)==[]
    assert not exact_formal_selection_complete(q,rows)

def test_explicit_id_still_respects_human_validation(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda _: {})
    row=record("INT-2026-000007",review_status="Pending Review")
    assert select_assistant_records("validated INT-2026-000007",[row])==[]

def test_explicit_id_over_limit_is_not_partial(monkeypatch):
    monkeypatch.setattr(intel,"human_approved_triage",lambda _: {})
    rows=[record(f"INT-2026-{i:06d}") for i in range(1,13)]
    q="Compare "+" ".join(f"INT-2026-{i:06d}" for i in range(1,13))
    assert select_assistant_records(q,rows,limit=10)==[]

def test_compound_place_separators_are_equivalent():
    assert formal_source_term_score(["jawa","timur"],"Jawa-Timur","") == \
           formal_source_term_score(["jawa","timur"],"Jawa Timur","")
    assert formal_source_term_score(["sumatera","selatan"],"Sumatera-Selatan","")>0
    assert formal_source_term_score(["riau"],"Keriau","")==0

def test_no_id_substitution_in_v2_endpoint(monkeypatch):
    from app import main,domain,campaigns,assistant_knowledge,intelligence_assistant
    from app.models import User
    from test_management_briefings_v1468 import dataset
    db=dataset()
    try:
        user=db.get(User,2)
        monkeypatch.setattr(main,"profile",lambda *_:{
            "status":"Active","permissions":{"view_intelligence":True},"province":"Riau"})
        monkeypatch.setattr(domain,"list_intelligence",lambda *_:[
            record("INT-2026-000007")])
        monkeypatch.setattr(intelligence_assistant,"human_approved_triage",lambda _: {})
        monkeypatch.setattr(assistant_knowledge,"authorized_reference_catalog",lambda *_: [])
        monkeypatch.setattr(assistant_knowledge,"retrieve_chat_knowledge",lambda *_args,**_kwargs:[])
        monkeypatch.setattr(campaigns,"campaign_action",lambda *_args,**_kwargs:{"findings":[]})
        def no_general(*args,**kwargs):
            raise AssertionError("Missing exact ID must never call general GPT")
        monkeypatch.setattr(intelligence_assistant,"generate_general_openai_answer",no_general)
        response=main.intelligence_assistant({
            "question":"Compare [INT-2026-000007] and [INT-2026-000009]",
            "analysisMode":"DATA","responseDepth":"DEEP"},user=user,db=db)
        assert response["provider"]["fallback_code"]=="no_matching_evidence"
        assert response["records"]==[]
        assert response["grounding"]["scope"]=="AUTHORIZED_EVIDENCE_NO_MATCH"
    finally:
        db.close()
