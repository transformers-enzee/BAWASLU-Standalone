"""Build 64.3 scheduler integration — simulated providers only, zero network."""
import os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock
import pytest
from app.db import Base,engine,SessionLocal
from app.models import (MonitoringCampaign,CampaignRun,CampaignEvidence,
                        SocialListeningResult,SocialListeningRun,SocialListeningProviderUsage)
from app.campaign_scheduler import (campaign_schedule_preview,campaign_history,
                                    simulate_campaign_cycle)
from app.socialcrawl import social_listening_action
from test_campaigns_v2 import actor,payload,action

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def active(db,p,**changes):
    config=payload(platforms=['tiktok'],primary_keywords=['pemilu','Gibran'],
                   excluded_keywords=['concert'],**changes)
    result=action(db,p,'createCampaign',config)['campaign']
    campaign=db.get(MonitoringCampaign,int(result['id']))
    campaign.status='ACTIVE'  # Synthetic-only; no HTTP route activates campaigns.
    campaign.next_run_at=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=1)
    db.commit()
    return campaign

def fake_provider(_):
    return {'success':True,'request_id':'mocked-scheduler-1','credits_used':1,
            'credits_remaining':999,'cached':False,'data':{'items':[
                {'id':'post-1','platform':'tiktok','url':'https://tiktok.com/@a/video/1',
                 'text':'Pemilu update on Gibran and election monitoring',
                 'language':'id','author':{'name':'A','handle':'@a'}}]}}

def test_preview_is_read_only_and_default_denies_paid_crawling(monkeypatch):
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=active(db,p)
    monkeypatch.delenv('BAWASLU_CRAWL_DAILY_CREDIT_BUDGET',raising=False)
    monkeypatch.delenv('BAWASLU_CRAWL_PER_RUN_CREDIT_LIMIT',raising=False)
    preview=action(db,p,'campaignSchedulePreview',{},str(c.id))['schedule']
    assert preview['is_due'] is True
    assert preview['automatic_paid_crawling_enabled'] is False
    assert preview['can_run_paid'] is False
    assert preview['estimated_credits_per_run']==1
    assert preview['credits_used_last_24h']==0
    assert len(preview['blocked_reasons'])>=2
    assert c.next_run_at.isoformat()==preview['next_crawl_at']
    assert action(db,p,'campaignHistory',{},str(c.id))['history']==[]
    assert db.query(SocialListeningRun).count()==0
    db.close()

def test_global_spend_counts_manual_provider_queries(monkeypatch):
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=active(db,p)
    db.add(SocialListeningProviderUsage(provider='SOCIALCRAWL',
        credits_used=9,user_id=p['id'],created_at=datetime.utcnow()))
    db.commit()
    monkeypatch.setenv('BAWASLU_CRAWL_DAILY_CREDIT_BUDGET','9')
    monkeypatch.setenv('BAWASLU_CRAWL_PER_RUN_CREDIT_LIMIT','2')
    preview=campaign_schedule_preview(db,c)
    assert preview['credits_used_last_24h']==9
    assert preview['credits_available_in_budget']==0
    assert any('24-hour' in reason for reason in preview['blocked_reasons'])
    assert preview['can_run_paid'] is False
    db.close()

def test_simulation_requires_fake_provider_and_positive_budget():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=active(db,p)
    with pytest.raises(ValueError,match='injected test provider'):
        simulate_campaign_cycle(db,p,c)
    client=Mock(side_effect=AssertionError('Should not call provider'))
    assert simulate_campaign_cycle(db,p,c,client)['status']=='BLOCKED'
    client.assert_not_called()
    assert simulate_campaign_cycle(db,p,c,client,daily_budget=1,per_run_limit=0)['status']=='BLOCKED'
    client.assert_not_called()
    assert db.query(CampaignRun).count()==0
    db.close()

def test_two_campaigns_link_same_source_once_without_duplication():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    one=active(db,p)
    two=active(db,p)
    call=Mock(side_effect=fake_provider)
    now=datetime.utcnow()
    x=simulate_campaign_cycle(db,p,one,call,now,daily_budget=5,per_run_limit=2)
    y=simulate_campaign_cycle(db,p,two,call,now,daily_budget=5,per_run_limit=2)
    assert x['status']==y['status']=='COMPLETED'
    assert x['linked_new_evidence']==1 and y['linked_new_evidence']==1
    assert db.query(SocialListeningResult).count()==1
    assert db.query(CampaignEvidence).count()==2
    assert db.query(CampaignRun).count()==2
    assert db.query(SocialListeningProviderUsage).count()==2
    assert db.query(CampaignEvidence).filter(CampaignEvidence.result_id==1).count()==2
    assert one.last_success_at==now
    assert one.next_run_at==now+timedelta(minutes=one.interval_minutes)
    assert call.call_count==2
    assert len(campaign_history(db,one))==1
    db.close()

def test_synthetic_failure_recorded_and_bounded_retry_backoff():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=active(db,p)
    def outage(_): raise RuntimeError('synthetic provider outage')
    now=datetime.utcnow()
    a=simulate_campaign_cycle(db,p,c,outage,now,daily_budget=3,per_run_limit=2)
    assert a['status']=='FAILED'
    assert c.next_run_at==now+timedelta(minutes=15)
    assert c.last_success_at is None
    c.next_run_at=now-timedelta(seconds=1);db.commit()
    b=simulate_campaign_cycle(db,p,c,outage,now,daily_budget=3,per_run_limit=2)
    assert b['status']=='FAILED'
    assert c.next_run_at==now+timedelta(minutes=30)
    assert db.query(CampaignRun).count()==2
    assert [x['status'] for x in campaign_history(db,c)]==['FAILED','FAILED']
    assert db.query(SocialListeningResult).count()==0
    db.close()

def test_out_of_scope_campaign_cannot_preview_or_simulate():
    db=SessionLocal()
    bali=actor(db,'bali','Provincial Analyst','Province','Bali')
    java=actor(db,'java','Provincial Analyst','Province','Jawa Barat')
    c=active(db,bali)
    with pytest.raises(ValueError,match='not available'):
        action(db,java,'campaignSchedulePreview',{},str(c.id))
    with pytest.raises(ValueError,match='not available'):
        action(db,java,'campaignHistory',{},str(c.id))
    with pytest.raises(PermissionError):
        simulate_campaign_cycle(db,java,c,fake_provider,daily_budget=5,per_run_limit=2)
    assert db.query(SocialListeningRun).count()==0
    db.close()

def test_keyword_exclusion_does_not_link_unrelated_post():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=active(db,p)
    def soundtrack(_):
        r=fake_provider(_)
        r['data']['items'][0]['text']='Gibran concert music performance'
        return r
    now=datetime.utcnow()
    outcome=simulate_campaign_cycle(db,p,c,soundtrack,now,daily_budget=5,per_run_limit=2)
    assert outcome['status']=='COMPLETED'
    assert outcome['linked_new_evidence']==0
    assert db.query(CampaignEvidence).count()==0
    db.close()
