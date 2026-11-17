"""v165.7 read-only, source-safe campaign worker readiness and budget guard."""
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,AIBudgetReservation,SocialListeningResult
from app.campaign_ai_readiness import campaign_ai_worker_readiness

def fixture():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    return e,Session(e)

def add(db,cid,rid,state='PENDING',method='KEYWORD',text='original evidence',attempts=0):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    if text is not None:
        db.add(SocialListeningResult(id=rid,run_id=1,text_content=text))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=attempts))
    db.flush()

def settings(**kwargs):
    base={'BAWASLU_AI_WORKER_ENABLED':'true',
          'BAWASLU_AUTO_AI_SCREENING_ENABLED':'true',
          'OPENAI_API_KEY':'test-configured-only',
          'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'10',
          'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'20',
          'BAWASLU_AI_ASSESSMENTS_PER_RUN':'5'}
    base.update(kwargs)
    return base

def test_all_job_states_source_and_campaign_scope():
    e,db=fixture()
    try:
        add(db,2,1)
        add(db,2,2,text=None)
        add(db,2,3,text='   ')
        add(db,2,4,state='PENDING',attempts=3)
        add(db,2,5,state='PROCESSING')
        add(db,2,6,state='COMPLETED')
        add(db,2,7,state='FAILED')
        add(db,2,8,method='WATCHLIST_ACCOUNT')
        add(db,3,9)
        result=campaign_ai_worker_readiness(db,2,settings())
        q=result['queue_counts']
        assert q=={'ordinary_jobs':7,'pending':4,
                   'claimable_pending_with_text':1,
                   'pending_missing_source_or_text':2,
                   'pending_attempts_exhausted':1,
                   'processing':1,'completed':1,'failed':1}
        assert not result['ready_to_process']  # SQLite must never authorize AI billing.
        assert 'POSTGRES_RESERVATION_REQUIRED' in result['readiness_blockers']
        assert result['estimated_max_requests_next_run']==0
        assert result['database_writes']==0 and not result['paid_provider_called']
    finally:db.close();e.dispose()

def test_aggregate_reservations_and_exhausted_budget_fail_closed():
    e,db=fixture()
    try:
        add(db,2,1)
        today=datetime.utcnow().strftime('%Y-%m-%d')
        db.add(AIBudgetReservation(campaign_id=2,budget_period=today,reserved_requests=10))
        db.add(AIBudgetReservation(campaign_id=2,budget_period='lifetime',reserved_requests=12))
        db.add(AIBudgetReservation(campaign_id=3,budget_period='lifetime',reserved_requests=99))
        db.flush()
        result=campaign_ai_worker_readiness(db,2,settings())
        assert result['daily_remaining']==0
        assert result['lifetime_remaining']==8
        assert result['estimated_max_requests_next_run']==0
        assert 'AI_REQUEST_BUDGET_EXHAUSTED' in result['readiness_blockers']
        assert result['daily_reserved']==10 and result['lifetime_reserved']==12
    finally:db.close();e.dispose()

def test_missing_configuration_and_empty_queue_are_explicit():
    e,db=fixture()
    try:
        result=campaign_ai_worker_readiness(db,4,settings(
            BAWASLU_AI_WORKER_ENABLED='false',OPENAI_API_KEY='',
            BAWASLU_AI_ASSESSMENTS_PER_RUN='0'))
        assert {'WORKER_DISABLED','AI_PROVIDER_NOT_CONFIGURED',
                'PER_RUN_LIMIT_ZERO','NO_CLAIMABLE_JOBS'}.issubset(
                    set(result['readiness_blockers']))
        assert result['queue_counts']['ordinary_jobs']==0
        assert result['readiness_is_authorization'] is False
    finally:db.close();e.dispose()

def test_worker_skips_missing_or_blank_content_before_claim():
    from pathlib import Path
    worker=(Path(__file__).parents[1]/'app'/'auto_relevance.py').read_text()
    assert "if not item or not (item.text_content or '').strip():continue" in worker
    assert worker.index("if not item or not (item.text_content or '').strip():continue") < worker.index("claimed=db.execute(update(AIAssessmentJob)")
