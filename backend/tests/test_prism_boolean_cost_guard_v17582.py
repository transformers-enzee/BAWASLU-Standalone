"""No-credit regression for Boolean Prism planning and manual budget approval.

All provider calls are mocked; SQLite is in-memory. Nothing touches live
Supabase, SocialCrawl or OpenAI.
"""
import json
import os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from types import SimpleNamespace

import pytest

from app.project_boolean import discover_boolean_plan, encode_boolean_project_query
from app import prism_discover
from app.db import Base,engine,SessionLocal
from app.models import MonitoringCampaign,SocialListeningRun,CampaignRun,SocialListeningResult


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def new_campaign(db, expression='BAWASLU AND (Bandung OR "Jawa Barat") AND NOT hoaks'):
    c=MonitoringCampaign(name='Bandung BAWASLU',created_by='qa-officer',
        primary_keywords_json=encode_boolean_project_query(expression),
        secondary_keywords_json='[]',excluded_keywords_json='[]',
        platforms_json='["instagram","tiktok","online_news"]',
        status='DRAFT')
    db.add(c);db.commit()
    return c


def test_bandung_queries_geography_instead_of_broad_bawaslu():
    plan=discover_boolean_plan('BAWASLU AND (Bandung OR "Jawa Barat") AND NOT hoaks')
    assert plan['keywords']==['bandung','jawa barat']
    assert plan['contains']=='bawaslu'
    assert plan['exclude_terms']==['hoaks']
    assert plan['provider_boolean_native'] is False


def test_safe_retrieval_never_requires_or_branch_literal_as_mandatory():
    plan=discover_boolean_plan('(BAWASLU AND Bandung) OR ("Jawa Barat" AND KPU)')
    assert len(plan['keywords'])<=5
    assert plan['contains']==''
    assert plan['exclude_terms']==[]
    assert any(w in plan['keywords'] for w in ('bawaslu','bandung'))
    assert any(w in plan['keywords'] for w in ('jawa barat','kpu'))


def test_negated_or_arm_cannot_be_the_only_retrieval_path():
    plan=discover_boolean_plan('BAWASLU AND (NOT hoaks OR Bandung)')
    assert plan['keywords']==['bawaslu']
    assert plan['contains']==''
    assert plan['exclude_terms']==[]


def test_provider_body_uses_supported_fields_and_tighter_default_cap():
    c=SimpleNamespace(id=22,name='Bandung BAWASLU',description='',
         primary_keywords_json=encode_boolean_project_query(
             'BAWASLU AND (Bandung OR "Jawa Barat") AND NOT hoaks'),
         platforms_json='["instagram","tiktok","online_news"]')
    # body_for uses db only when it looks for prior completed runs.
    class Query:
        def join(self,*args):return self
        def filter(self,*args):return self
        def order_by(self,*args):return self
        def limit(self,*args):return self
        def all(self):return []
    class DB:
        def query(self,*args):return Query()
    params,signature=prism_discover.body_for(DB(),c)
    assert params['groups'][0]['keywords']==['bandung','jawa barat']
    assert params['groups'][0]['exclude_terms']==['hoaks']
    assert params['contains']=='bawaslu'
    assert params['max_credits']==20
    assert params['platforms']==['instagram','tiktok','news']
    assert params['limit']==100
    assert len(signature)==64
    c.platforms_json='["tiktok","instagram","youtube","facebook","twitter-ai-search","threads","online_news"]'
    focused,focused_signature=prism_discover.body_for(DB(),c)
    assert focused['platforms']==['instagram','tiktok','threads']
    all_sources,all_signature=prism_discover.body_for(DB(),c,20,'ALL')
    assert len(all_sources['platforms'])==7
    assert focused_signature!=all_signature
    with pytest.raises(ValueError):
        prism_discover.body_for(DB(),c,250)


def test_preview_is_free_and_zero_yield_requires_explicit_cap_and_acknowledgement(monkeypatch):
    db=SessionLocal()
    c=new_campaign(db)
    previous=SocialListeningRun(provider='SOCIALCRAWL_PRISM',executed_by='qa-officer',
        status='COMPLETED',credits_used=35,result_count=0,
        query_json=json.dumps({'body':{'groups':[{'keywords':['bawaslu']}],
                                 'platforms':['instagram','tiktok','news'],
                                 'max_credits':100},'campaign_id':c.id}))
    db.add(previous);db.flush()
    db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=previous.id,triggered_by='PRISM_DISCOVER'))
    db.add(SocialListeningResult(run_id=previous.id,provider='SOCIALCRAWL_PRISM',
        provider_result_id='prior-no-match',platform='news',
        text_content='BAWASLU nasional tetapi tidak membahas lokasi Bandung'))
    db.commit()

    # Authorization is tested by the real campaign() elsewhere; isolate
    # the billing/preview gates here and never use real provider credentials.
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    calls=[]
    def no_credit_provider(method,url,body=None,timeout=50):
        calls.append(body)
        assert body['dry_run'] is True
        return {'estimate':{'max_credits':body['max_credits'],'dry_run':True}}, {'request_id':'mock-free-preview'}
    monkeypatch.setattr(prism_discover,'call',no_credit_provider)
    args={'max_credits':20}
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',args,c.id)
    assert preview['credit_cap']==20
    assert preview['platform_mode']=='FOCUSED'
    assert preview['keywords_used']==['bandung','jawa barat']
    assert preview['provider_contains']=='bawaslu'
    assert preview['provider_exclude_terms']==['hoaks']
    assert preview['last_run']['newly_saved_source_rows']==1
    assert preview['last_run']['matched']==0
    assert preview['last_run']['credits_used']==35
    assert preview['last_run']['plan_changed'] is True
    assert preview['zero_yield_ack_required'] is True
    assert calls and all(x.get('dry_run') for x in calls)
    assert db.query(SocialListeningRun).count()==1

    valid={'max_credits':20,'confirm_cost':True,
           'signature':preview['signature'],'confirmed_max_credits':20,
           'platform_mode':'FOCUSED','confirmed_platform_mode':'FOCUSED'}
    with pytest.raises(ValueError,match='zero posts'):
        prism_discover.action(db,{},'campaignDiscoverStart',valid,c.id)
    with pytest.raises(ValueError,match='Credit cap changed'):
        prism_discover.action(db,{},'campaignDiscoverStart',
            {**valid,'confirmed_max_credits':100,'acknowledge_zero_yield':True},c.id)
    with pytest.raises(ValueError,match='free credit preview'):
        prism_discover.action(db,{},'campaignDiscoverStart',
            {**valid,'max_credits':35,'acknowledge_zero_yield':True},c.id)
    with pytest.raises(ValueError,match='Source selection changed'):
        prism_discover.action(db,{},'campaignDiscoverStart',
            {**valid,'confirmed_platform_mode':'ALL','acknowledge_zero_yield':True},c.id)
    assert db.query(SocialListeningRun).count()==1
    accepted=prism_discover.action(db,{},'campaignDiscoverStart',
        {**valid,'acknowledge_zero_yield':True},c.id)
    assert accepted['started'] is True
    assert accepted['credit_cap']==20
    assert db.query(SocialListeningRun).count()==2
    assert len(calls)==1  # Starting enqueues; does not itself make provider calls.
    db.close()
