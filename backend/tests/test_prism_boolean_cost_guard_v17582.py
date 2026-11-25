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


def test_bandung_compound_queries_instead_of_geographic_only():
    plan=discover_boolean_plan('BAWASLU AND (Bandung OR "Jawa Barat") AND NOT hoaks')
    assert plan['keywords']==['bawaslu','bawaslu bandung','bawaslu jawa barat']
    assert plan['contains']==''
    assert plan['exclude_terms']==[]
    assert plan['provider_boolean_native'] is False


def test_safe_retrieval_never_requires_or_branch_literal_as_mandatory():
    plan=discover_boolean_plan('(BAWASLU AND Bandung) OR ("Jawa Barat" AND KPU)')
    assert len(plan['keywords'])<=5
    assert plan['contains']==''
    assert plan['exclude_terms']==[]
    assert plan['keywords']==['bawaslu','jawa barat','bawaslu bandung','jawa barat kpu']


def test_negated_or_arm_cannot_be_the_only_retrieval_path():
    plan=discover_boolean_plan('BAWASLU AND (NOT hoaks OR Bandung)')
    assert plan['keywords']==['bawaslu']
    assert plan['contains']==''
    assert plan['exclude_terms']==[]


def test_provider_body_uses_supported_fields_and_standard_cap():
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
    assert params['groups'][0]['keywords']==['bawaslu','bawaslu bandung','bawaslu jawa barat']
    assert 'exclude_terms' not in params['groups'][0]
    assert 'contains' not in params
    assert params['relevance']=='score'
    assert params['period']=='30d'
    assert params['max_credits']==100
    assert params['platforms']==['instagram','tiktok','news']
    assert params['limit']==prism_discover.CANDIDATE_CAP
    assert len(signature)==64
    c.platforms_json='["tiktok","instagram","youtube","facebook","twitter-ai-search","threads","online_news"]'
    all_sources,all_signature=prism_discover.body_for(DB(),c)
    assert len(all_sources['platforms'])==7
    c.date_from='2025-07-16';c.date_to='2026-11-24'
    dated,dated_signature=prism_discover.body_for(DB(),c)
    assert dated['since']=='2025-07-16' and dated['until']=='2026-11-24'
    assert 'period' not in dated and dated_signature!=all_signature
    with pytest.raises(ValueError):prism_discover.body_for(DB(),c,20,'FOCUSED')
    with pytest.raises(ValueError):
        prism_discover.body_for(DB(),c,250)


def test_preview_is_free_and_signature_guard_remains_without_extra_ack(monkeypatch):
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
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    calls=[]
    def no_credit_provider(method,url,body=None,timeout=50):
        calls.append(body)
        assert body['dry_run'] is True
        return {'estimate':{'max_credits':body['max_credits'],'dry_run':True}}, {'request_id':'mock-free-preview'}
    monkeypatch.setattr(prism_discover,'call',no_credit_provider)
    args={}
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',args,c.id)
    assert preview['credit_cap']==100
    assert preview['platform_mode']=='ALL'
    assert preview['keywords_used']==['bawaslu','bawaslu bandung','bawaslu jawa barat']
    assert preview['provider_contains']==''
    assert preview['provider_exclude_terms']==[]
    assert preview['last_run']['newly_saved_source_rows']==1
    assert preview['last_run']['matched']==0
    assert preview['last_run']['credits_used']==35
    assert preview['last_run']['plan_changed'] is True
    assert preview['zero_yield_ack_required'] is False
    assert calls and all(x.get('dry_run') for x in calls)
    assert db.query(SocialListeningRun).count()==1

    valid={'confirm_cost':True,'signature':preview['signature']}
    with pytest.raises(ValueError,match='free credit preview'):
        prism_discover.action(db,{},'campaignDiscoverStart',{**valid,'max_credits':35},c.id)
    with pytest.raises(ValueError,match='free credit preview'):
        prism_discover.action(db,{},'campaignDiscoverStart',{**valid,'confirm_cost':False},c.id)
    assert db.query(SocialListeningRun).count()==1
    accepted=prism_discover.action(db,{},'campaignDiscoverStart',valid,c.id)
    assert accepted['started'] is True
    assert accepted['credit_cap']==100
    assert db.query(SocialListeningRun).count()==2
    assert len(calls)==1  # Starting enqueues; does not itself make provider calls.
    db.close()


def test_run39_aggregate_diagnostics_without_provider_calls():
    d=prism_discover.provider_diagnostics({'summary':{
        'rows':{'returned':521,'collected':519,'kept':0,'dropped':519},
        'dropped':{'out_of_window':82,'off_topic':1,'filter':436,
                   'by_filter':{'base':'collected_rows','filter:contains':429,'filter:country':7}},
        'by_platform':{'instagram':{'rows':{'collected':77}}}}})
    assert d['returned']==521 and d['kept']==0
    assert d['by_filter']=={'filter:contains':429,'filter:country':7}
    assert d['by_platform']=={'instagram':77}


def test_duplicate_start_is_blocked(monkeypatch):
    db=SessionLocal();c=new_campaign(db)
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    monkeypatch.setattr(prism_discover,'call',lambda *a,**k: ({'estimate':{}},{}))
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',{},c.id)
    data={'signature':preview['signature'],'confirm_cost':True}
    assert prism_discover.action(db,{},'campaignDiscoverStart',data,c.id)['started']
    with pytest.raises(ValueError,match='already active'):
        prism_discover.action(db,{},'campaignDiscoverStart',data,c.id)
    assert db.query(SocialListeningRun).count()==1
    db.close()


def test_identical_same_scope_provider_group_and_anchor_coverage():
    db=SessionLocal();a=new_campaign(db);b=new_campaign(db)
    pa,_=prism_discover.body_for(db,a);pb,_=prism_discover.body_for(db,b)
    assert pa==pb
    b.province='Jawa Barat';db.commit()
    other,_=prism_discover.body_for(db,b)
    assert other['groups'][0]['id']!=pa['groups'][0]['id']
    assert 'bawaslu' in pa['groups'][0]['keywords']
    assert len(pa['groups'][0]['keywords'])<=5
    db.close()


def test_monthly_and_storage_guard_blocks_before_provider_preview(monkeypatch):
    db=SessionLocal();c=new_campaign(db)
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT','200')
    monkeypatch.setattr(prism_discover,'call',lambda *a,**k:pytest.fail('no provider call allowed'))
    with pytest.raises(ValueError,match='Monthly collection allowance'):
        prism_discover.action(db,{},'campaignDiscoverPreview',{},c.id)
    monkeypatch.setenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT','3000000')
    monkeypatch.setenv('BAWASLU_ACTIVE_SOURCE_STORAGE_LIMIT','200')
    with pytest.raises(ValueError,match='Active source storage allowance'):
        prism_discover.action(db,{},'campaignDiscoverPreview',{},c.id)
    db.close()
