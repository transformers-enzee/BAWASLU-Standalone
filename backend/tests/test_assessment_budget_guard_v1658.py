"""v165.8: no paid provider path may bypass campaign quota reservation."""
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest
from app.db import Base
from app.models import AIAssessmentJob
from app.auto_relevance import release_unbilled_claim, reserve_automatic_ai_request

def _setup():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

@pytest.mark.parametrize('reanalysis,expected',[(False,'PENDING'),(True,'COMPLETED')])
def test_denied_budget_restores_claim_without_consuming_retry(reanalysis,expected):
    engine,db=_setup()
    try:
        job=AIAssessmentJob(campaign_id=2,result_id=22,
                            state='PROCESSING',attempts=2)
        db.add(job);db.commit()
        assert reserve_automatic_ai_request(db,2) is False
        release_unbilled_claim(db,job,reanalysis=reanalysis)
        db.refresh(job)
        assert job.state==expected
        assert job.attempts==1
        assert 'no provider request' in job.last_error
    finally:
        db.close();engine.dispose()

def test_release_is_fail_closed_for_unclaimed_job():
    engine,db=_setup()
    try:
        job=AIAssessmentJob(campaign_id=2,result_id=23,
                            state='PENDING',attempts=0)
        db.add(job);db.commit()
        with pytest.raises(ValueError):
            release_unbilled_claim(db,job)
        assert job.state=='PENDING' and job.attempts==0
    finally:
        db.close();engine.dispose()

def test_every_worker_path_reserves_before_provider():
    source=(Path(__file__).parents[1]/'app'/'auto_relevance.py').read_text()
    begin=source.index('def _assess_pending_campaign_locked(')
    end=source.index('\ndef assess_pending_campaign(',begin)
    body=source[begin:end]
    assert "if not reserve_automatic_ai_request(db,campaign.id):" in body
    assert "release_unbilled_claim(db,job,reanalysis=reanalysis)" in body
    assert 'requested_limit is None or target_result_id is not None) and not reserve_' not in body
    assert body.index('if not reserve_automatic_ai_request') < body.index('response=httpx.post(')
    assert body.index("if not item or not (item.text_content or '').strip():continue") < body.index('if not reserve_automatic_ai_request')
