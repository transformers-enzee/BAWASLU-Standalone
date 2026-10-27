"""QA retains explicit per-click limits; lifetime and daily counters are informational."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app.smart_radar_qa_limits import qa_config, qa_readiness, ensure_qa_batch

class _BudgetRow:
    def __init__(self,used_today=0,used_lifetime=0):
        self.n={"used_today":used_today,"used_lifetime":used_lifetime}
    def mappings(self):return self
    def first(self):return self.n
class _DB:
    def __init__(self,today=0,lifetime=0):self.today=today;self.lifetime=lifetime
    def execute(self,query):
        assert "pilot_smart_radar.qa_ai_assessments" in str(query)
        return _BudgetRow(self.today,self.lifetime)

def test_existing_env_model_and_budget(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL","gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY","test-placeholder")
    monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","3")
    monkeypatch.setenv("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN","8")
    monkeypatch.setenv("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN","12")
    monkeypatch.delenv("SMART_RADAR_QA_MODEL",raising=False)
    monkeypatch.delenv("SMART_RADAR_QA_AI_ENABLED",raising=False)
    cfg=ensure_qa_batch(_DB(today=2,lifetime=7),3)
    assert cfg["model"]=="gpt-4o-mini"
    assert cfg["model_source"]=="OPENAI_MODEL"
    assert cfg["daily_remaining"] is None
    assert cfg["daily"] is None
    assert cfg["used_today"]==2
    assert cfg["lifetime_remaining"]>200
    assert cfg["max_run"]==3

def test_worker_flags_do_not_implicitly_trigger_or_block_admin_qa(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test-placeholder")
    monkeypatch.setenv("OPENAI_MODEL","gpt-4o-mini")
    monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","3")
    monkeypatch.setenv("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN","5")
    monkeypatch.setenv("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN","8")
    monkeypatch.setenv("BAWASLU_AI_WORKER_ENABLED","false")
    monkeypatch.setenv("BAWASLU_AUTO_AI_SCREENING_ENABLED","false")
    assert qa_readiness(_DB())["ready"] is True

def test_existing_limits_fail_closed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test-placeholder")
    monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","0")
    with pytest.raises(HTTPException) as err:
        ensure_qa_batch(_DB(),1)
    assert err.value.status_code==409
    monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","invalid")
    with pytest.raises(HTTPException):
        ensure_qa_batch(_DB(),1)

def test_daily_and_lifetime_limits_do_not_block_admin_qa(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test-placeholder")
    monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","3")
    monkeypatch.setenv("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN","4")
    monkeypatch.setenv("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN","8")
    # Legacy campaign daily env must NOT restrict manual QA experimentation.
    assert ensure_qa_batch(_DB(today=400,lifetime=3),2)["used_today"]==400
    assert qa_readiness(_DB(today=400,lifetime=3))["ready"] is True
    assert ensure_qa_batch(_DB(today=400,lifetime=700),2)["used_lifetime"]==700

def test_hard_maximums_are_conservative(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY","test-placeholder")
    monkeypatch.setenv("BAWASLU_AI_ASSESSMENTS_PER_RUN","100")
    monkeypatch.setenv("BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN","300")
    monkeypatch.setenv("BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN","999")
    cfg=qa_config()
    assert cfg["max_run"]==3
    assert cfg["daily"] is None
    assert cfg["lifetime"] is None
