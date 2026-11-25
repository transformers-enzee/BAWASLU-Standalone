"""v183.8: live-model QA must be opt-in, capped, synthetic and isolated."""
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import intelligence_assessment_live_qa as live
from app.intelligence_assessment_qa import LOOKUP
from app.db import Base
from app.models import AuditEvent


def test_live_disabled_by_default_and_invalid_limits_fail_closed(monkeypatch):
    monkeypatch.delenv("BAWASLU_ASSESSMENT_QA_LIVE_AI_ENABLED",raising=False)
    monkeypatch.setenv("OPENAI_API_KEY","mock-secret")
    monkeypatch.setenv("BAWASLU_ASSESSMENT_QA_LIVE_DAILY_LIMIT","invalid")
    cfg=live.live_config()
    assert cfg["enabled"] is False
    assert cfg["daily_limit"]==0


def test_explicit_limits_are_bounded(monkeypatch):
    monkeypatch.setenv("BAWASLU_ASSESSMENT_QA_LIVE_AI_ENABLED","1")
    monkeypatch.setenv("BAWASLU_ASSESSMENT_QA_LIVE_DAILY_LIMIT","99999")
    monkeypatch.setenv("BAWASLU_ASSESSMENT_QA_LIVE_TOTAL_LIMIT","99999")
    cfg=live.live_config()
    assert cfg["enabled"] is True
    assert cfg["daily_limit"]==8
    assert cfg["total_limit"]==24


def test_no_provider_calls_when_disabled_or_invalid_case(monkeypatch):
    called=[]
    monkeypatch.setattr(live,"require_national_admin",lambda db,user:{"role":"National Administrator"})
    monkeypatch.setattr(live.httpx,"post",lambda *a,**k:called.append(1))
    monkeypatch.delenv("BAWASLU_ASSESSMENT_QA_LIVE_AI_ENABLED",raising=False)
    monkeypatch.setenv("OPENAI_API_KEY","mock-secret")
    for case_id,code in (("money-politics",409),("does-not-exist",404),("approved-override",409)):
        with pytest.raises(HTTPException) as exc:
            live.run_synthetic_ai(live.LiveRequest(case_id=case_id),user=object(),db=None)
        assert exc.value.status_code==code
    assert called==[]


def test_provider_receives_only_server_owned_synthetic_text(monkeypatch):
    monkeypatch.setattr(live,"require_national_admin",lambda db,user:True)
    monkeypatch.setenv("BAWASLU_ASSESSMENT_QA_LIVE_AI_ENABLED","1")
    monkeypatch.setenv("OPENAI_API_KEY","mock-secret")
    monkeypatch.setenv("OPENAI_MODEL","gpt-4o-mini")
    monkeypatch.setattr(live,"reserve_attempt",lambda db,user,case_id,cfg:None)
    sent=[]
    class FakeResponse:
        def raise_for_status(self):return None
        def json(self):
            case=LOOKUP["money-politics"]
            return {"choices":[{"message":{"content":json.dumps({
                "predictions":dict(case["expected"]),
                "summary":"Tuduhan belum diverifikasi",
                "recommended_check":"Periksa bukti dan sumber mandiri",
                "evidence_quote":case["source_text"][:12]
            })}}],"usage":{"prompt_tokens":123,"completion_tokens":88}}
    def fake_post(url,**kwargs):
        sent.append({"url":url,"payload":kwargs["json"]})
        return FakeResponse()
    monkeypatch.setattr(live.httpx,"post",fake_post)
    out=live.run_synthetic_ai(live.LiveRequest(case_id="money-politics"),
                              user=object(),db=None)
    assert out["actual_model_called"] is True
    assert out["comparison"]["matched_fields"]==len(LOOKUP["money-politics"]["expected"])
    assert out["evidence_quote_verified"] is True
    assert out["predictions_persisted"] is False
    assert len(sent)==1
    message=sent[0]["payload"]["messages"][-1]["content"]
    assert LOOKUP["money-politics"]["source_text"] in message
    assert "expected" not in message.lower()  # no reference answers supplied
    assert all(str(v) not in message for v in ("substantiated_by_authority","uncorroborated"))


def test_non_postgres_cannot_make_paid_reservation():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        with pytest.raises(HTTPException) as exc:
            live.reserve_attempt(db,object(),"money-politics",live.live_config())
        assert exc.value.status_code==409
        assert db.query(AuditEvent).count()==0
    engine.dispose()


def test_read_only_budget_counts_qa_events_only():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(AuditEvent(subject_type=live._AUDIT_KIND,subject_id="SYNTH-X",
          action="PAID_SYNTHETIC_QA_CALL_RESERVED",actor_id="synthetic",
          actor_name="synthetic",changes_json="{}",occurred_at="2026-11-25T01:00:00+00:00"))
        db.add(AuditEvent(subject_type="OFFICER_ACTION",subject_id="1",
          action="OTHER",actor_id="synthetic",actor_name="synthetic",
          changes_json="{}",occurred_at="2026-11-25T01:00:00+00:00"))
        db.commit()
        result=live._remaining(db,{"daily_limit":3,"total_limit":24})
        assert result["total_used"]==1
        assert result["total_remaining"]==23
    engine.dispose()
