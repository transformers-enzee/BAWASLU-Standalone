"""v165.9: honest no-cost preview for authorized manual AI batches."""
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (CampaignEvidence,SocialListeningResult,EvidenceAssessment,
                        AIAssessmentJob,AIBudgetReservation)
from app.campaign_ai_readiness import campaign_manual_batch_preview

def fixture():
    eng=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(eng)
    return eng,Session(eng)

def env(**kw):
    out={'OPENAI_API_KEY':'configured','BAWASLU_AI_ASSESSMENTS_PER_RUN':'10',
         'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'5',
         'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'12'}
    out.update(kw)
    return out

def seed(db,cid,rid,method='KEYWORD',state='PENDING',label=None,txt='source'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    db.add(SocialListeningResult(id=rid,run_id=1,text_content=txt))
    if label is not None:
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
                                  assessment_version=1,relevance_label=label))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=0))
    db.flush()

def test_all_eligible_historical_queued_rows_count_without_latest_300_cap():
    eng,db=fixture()
    try:
        seed(db,2,1)
        for i in range(2,305):
            db.add(CampaignEvidence(campaign_id=2,result_id=i,match_method='KEYWORD'))
        db.flush()
        out=campaign_manual_batch_preview(db,2,10,env())
        assert out['eligible_queued_unassessed']==1
        assert out['historical_window_limit_applied'] is False
        assert out['estimated_ai_requests']==0  # SQLite: no paid authorization
        assert out['paid_provider_called'] is False and out['database_writes']==0
    finally:db.close();eng.dispose()

def test_relevance_watchlist_state_empty_text_and_other_campaign_excluded():
    eng,db=fixture()
    try:
        seed(db,2,1)
        seed(db,2,2,method='WATCHLIST_ACCOUNT')
        seed(db,2,3,state='FAILED')
        seed(db,2,4,label='RELEVANT')
        seed(db,2,5,txt='   ')
        seed(db,3,6)
        out=campaign_manual_batch_preview(db,2,20,env())
        assert out['eligible_queued_unassessed']==1
    finally:db.close();eng.dispose()

def test_daily_and_lifetime_budget_reported_without_any_spend():
    eng,db=fixture()
    try:
        seed(db,2,1)
        today=datetime.utcnow().strftime('%Y-%m-%d')
        db.add(AIBudgetReservation(campaign_id=2,budget_period=today,reserved_requests=4))
        db.add(AIBudgetReservation(campaign_id=2,budget_period='lifetime',reserved_requests=12))
        db.flush()
        out=campaign_manual_batch_preview(db,2,10,env())
        assert out['daily_remaining']==1 and out['lifetime_remaining']==0
        assert out['batch_limit']==0
    finally:db.close();eng.dispose()

def test_invalid_limits_fail_closed():
    eng,db=fixture()
    try:
        for v in (0,21,True,'5',1.5):
            try:campaign_manual_batch_preview(db,2,v,env())
            except ValueError:pass
            else:assert False,v
    finally:db.close();eng.dispose()

def test_api_rejects_unconfirmed_start_and_dispatch_is_deferred():
    from pathlib import Path
    p=Path(__file__).parents[1]/'app'
    c=(p/'campaigns.py').read_text()
    main=(p/'main.py').read_text()
    assert "if (data or {}).get('confirm_ai_cost') is not True" in c
    assert "if not preview['batch_limit']:" in c
    assert "assessment_job_accepted':True" in c
    assert "background_tasks.add_task(assess_pending_campaign,int(result['campaign_id']),int(result['batch_limit']))" in main
