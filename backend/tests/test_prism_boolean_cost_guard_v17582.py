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


def test_exact_recent_collection_reuse_is_explicit_and_free(monkeypatch):
    from app.models import CampaignEvidence,EvidenceAssessment
    db=SessionLocal();source=new_campaign(db);target=new_campaign(db)
    body,_=prism_discover.body_for(db,source)
    config=prism_discover.search_snapshot(source)
    run=SocialListeningRun(provider='SOCIALCRAWL_PRISM',status='COMPLETED',provider_request_id='run_original',credits_used=8,result_count=1)
    db.add(run);db.flush()
    db.add(CampaignRun(campaign_id=source.id,social_listening_run_id=run.id))
    row=SocialListeningResult(run_id=run.id,platform='instagram',text_content='BAWASLU Bandung',provider_result_id='reuse-1')
    db.add(row);db.flush()
    db.add(CampaignEvidence(campaign_id=source.id,result_id=row.id,match_method='PRISM_DISCOVER'))
    db.add(EvidenceAssessment(campaign_id=source.id,result_id=row.id,assessment_version=1,relevance_label='RELEVANT'))
    run.query_json=json.dumps({'body':body,'search_snapshot':config,'query_revision':prism_discover.snapshot_signature(config),
        'assessment_result_ids':[row.id],'collection_diagnostics':{'unique_candidates':1}})
    db.commit()
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:target)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    calls=[]
    def free(method,url,body=None,timeout=50):
        calls.append(method);assert body['dry_run'] is True
        return {'estimate':{}},{}
    monkeypatch.setattr(prism_discover,'call',free)
    principal={'geographic_scope':'Nationwide'}
    preview=prism_discover.action(db,principal,'campaignDiscoverPreview',{},target.id)
    assert preview['reuse_offer']['source_run_id']==run.id
    result=prism_discover.action(db,principal,'campaignDiscoverReuse',{'signature':preview['signature'],'source_run_id':run.id},target.id)
    assert result['new_links']==1 and result['credits_used']==0
    assert not result['paid_provider_called'] and not result['paid_ai_executed'] and calls==['POST']
    assert db.query(EvidenceAssessment).filter_by(campaign_id=target.id).count()==0
    assert db.query(CampaignEvidence).filter_by(campaign_id=target.id).count()==1
    db.close()


def test_uncertain_previous_charge_requires_explicit_ack_and_active_preview_is_read_only(monkeypatch):
    db=SessionLocal();c=new_campaign(db)
    run=SocialListeningRun(provider='SOCIALCRAWL_PRISM',status='FAILED',
        query_json=json.dumps({'campaign_id':c.id,'submission_uncertain':True}))
    db.add(run);db.flush();db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=run.id));db.commit()
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    calls=[]
    def free(method,url,body=None,timeout=50):
        assert body['dry_run'];calls.append(method);return {'estimate':{}},{}
    monkeypatch.setattr(prism_discover,'call',free)
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',{},c.id)
    assert preview['prior_collection_ack_required']
    payload={'confirm_cost':True,'signature':preview['signature']}
    with pytest.raises(ValueError,match='explicitly acknowledge'):
        prism_discover.action(db,{},'campaignDiscoverStart',payload,c.id)
    assert db.query(SocialListeningRun).count()==1
    started=prism_discover.action(db,{},'campaignDiscoverStart',{**payload,'acknowledge_prior_collection':True},c.id)
    resumed=prism_discover.action(db,{},'campaignDiscoverPreview',{},c.id)
    assert resumed['active_run_id']==str(started['run_id']) and resumed['paid_collection_blocked']
    assert calls==['POST']
    db.close()


def test_focused_boolean_strategy_and_credit_cap_are_signature_bound(monkeypatch):
    db=SessionLocal();c=new_campaign(db)
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    calls=[]
    def free(method,url,body=None,timeout=50):
        assert body['dry_run'];calls.append(body);return {'estimate':{}},{}
    monkeypatch.setattr(prism_discover,'call',free)
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',{'max_credits':10,'retrieval_strategy':'FOCUSED'},c.id)
    assert preview['keywords_used']==['bawaslu bandung','bawaslu jawa barat']
    assert preview['credit_cap']==10
    assert preview['provider_plan']['effective_strategy']=='FOCUSED'
    with pytest.raises(ValueError,match='free credit preview'):
        prism_discover.action(db,{},'campaignDiscoverStart',{'confirm_cost':True,'signature':preview['signature'],'max_credits':20,'retrieval_strategy':'FOCUSED'},c.id)
    with pytest.raises(ValueError,match='free credit preview'):
        prism_discover.action(db,{},'campaignDiscoverStart',{'confirm_cost':True,'signature':preview['signature'],'max_credits':10,'retrieval_strategy':'BALANCED'},c.id)
    assert db.query(SocialListeningRun).count()==0 and len(calls)==1
    db.close()


def test_production_collection_uses_provider_estimate_without_fixed_cap(monkeypatch):
    db=SessionLocal();c=new_campaign(db)
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    def free(method,url,body=None,timeout=50):
        assert body['dry_run'] and 'max_credits' not in body
        assert body['depth']=='deep' and body['limit']==5000
        return {'suggested_max_credits':987,'estimate':{'credits':{'max':987}}},{}
    monkeypatch.setattr(prism_discover,'call',free)
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',{'production_collection':True},c.id)
    assert preview['credit_cap']==987 and preview['post_limit'] is None
    result=prism_discover.action(db,{},'campaignDiscoverStart',{'production_collection':True,'confirm_cost':True,'signature':preview['signature'],'confirmed_credit_estimate':preview['credit_cap']},c.id)
    run=db.get(SocialListeningRun,result['run_id'])
    meta=json.loads(run.query_json)
    assert meta['full_collection'] and meta['body']['max_credits']==987
    assert meta['body']['limit']==5000 and meta['body']['depth']=='deep'
    # Completed full exports reuse the same configuration identity, regardless of spending allowance.
    run.status='COMPLETED';meta['watermark']='verified-watermark';meta['full_export_complete']=True
    run.query_json=json.dumps(meta);db.commit()
    next_body,_=prism_discover.body_for(db,c,production=True)
    assert next_body['since_watermark']=='verified-watermark'
    db.close()


def test_quota_policy_is_optional_not_hardcoded(monkeypatch):
    from app import prism_collection_budget as budget
    db=SessionLocal()
    monkeypatch.delenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT',raising=False)
    monkeypatch.delenv('BAWASLU_ACTIVE_SOURCE_STORAGE_LIMIT',raising=False)
    state=budget.assert_capacity(db,10000000)
    assert state['monthly_remaining'] is None and state['storage_remaining'] is None
    monkeypatch.setenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT','7000000')
    assert budget.snapshot(db)['monthly_limit']==7000000
    db.close()


def test_production_increased_estimate_requires_new_confirmation(monkeypatch):
    db=SessionLocal();c=new_campaign(db)
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    estimates=iter([700,900]);calls=[]
    def free(method,url,body=None,timeout=50):
        assert body['dry_run'] and 'max_credits' not in body
        calls.append(body)
        return {'suggested_max_credits':next(estimates)},{}
    monkeypatch.setattr(prism_discover,'call',free)
    preview=prism_discover.action(db,{},'campaignDiscoverPreview',{'production_collection':True},c.id)
    with pytest.raises(ValueError,match='credit estimate changed'):
        prism_discover.action(db,{},'campaignDiscoverStart',{'production_collection':True,'confirm_cost':True,'signature':preview['signature'],'confirmed_credit_estimate':700},c.id)
    assert len(calls)==2 and db.query(SocialListeningRun).count()==0
    db.close()


def test_production_reservation_uses_requested_delivery_size(monkeypatch):
    from app import prism_collection_budget as budget
    db=SessionLocal();c=new_campaign(db)
    monkeypatch.setenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT','10000')
    monkeypatch.setenv('BAWASLU_ACTIVE_SOURCE_STORAGE_LIMIT','10000')
    run=SocialListeningRun(provider='SOCIALCRAWL_PRISM',status='QUEUED',query_json=json.dumps({'full_collection':True,'body':{'limit':5000}}))
    db.add(run);db.commit()
    state=budget.snapshot(db)
    assert state['monthly_reserved']==5000 and state['storage_reserved']==5000
    assert state['monthly_remaining']==5000
    db.close()
