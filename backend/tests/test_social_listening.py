import json, os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app.db import Base, engine, SessionLocal
from app.models import User, AccessGrant, SocialListeningResult, SocialListeningProviderUsage, IntelligenceItem
from app.auth import hash_password
from app.access import default_permissions, profile
from app.socialcrawl import social_listening_action

def setup_function():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)

def admin(db):
    u=User(email='admin@sl.local',full_name='Admin',password_hash=hash_password('secret'),platform_admin=True); db.add(u); db.flush()
    db.add(AccessGrant(user_id=u.id,access_role='National Administrator',geographic_scope='Nationwide',permissions_json=json.dumps(default_permissions('National Administrator')),status='Active')); db.commit(); return profile(db,u)

def provincial_analyst(db,province='Bali'):
    u=User(email='analyst@sl.local',full_name='Provincial Analyst',password_hash=hash_password('secret')); db.add(u); db.flush()
    db.add(AccessGrant(user_id=u.id,access_role='Provincial Analyst',geographic_scope='Province',province=province,permissions_json=json.dumps(default_permissions('Provincial Analyst')),status='Active')); db.commit(); return profile(db,u)

def fake_provider(filters):
    return {'success':True,'request_id':'req-1','credits_used':20,'credits_remaining':980,'cached':False,'data':{'items':[
      {'id':'post-1','platform':'tiktok','url':'https://www.tiktok.com/@actor/video/1','author':{'name':'Actor','handle':'@actor'},'text':'Public election administration update in Jakarta','language':'id','relevance_score':0.91,'metrics':{'views':1000,'likes':100,'comments':10,'shares':5},'engagement_rate':0.115,'estimated_reach':1200},
      {'id':'post-2','platform':'youtube','url':'https://youtube.com/watch?v=x','author':{'name':'Channel','handle':'@channel'},'text':'Unrelated content','language':'en'}
    ]}}

def test_search_persists_provenance_usage_and_filters():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'election','language':'id','platforms':['tiktok','youtube'],'limit':25}},provider_client=fake_provider)
    assert len(r['results'])==1
    x=r['results'][0]
    assert x['provider']=='SOCIALCRAWL'
    assert x['platform']=='tiktok'
    assert x['source_identity']['status'] in ('KNOWN_EXTERNAL_ACCOUNT','UNRESOLVED','REGISTERED_ACCOUNT_CONFIRMED')
    assert db.query(SocialListeningResult).count()==1
    u=db.query(SocialListeningProviderUsage).one(); assert u.credits_used==20 and u.provider_request_id=='req-1'
    db.close()

def test_saved_rule_and_promotion_are_human_controlled():
    db=SessionLocal(); p=admin(db)
    rule=social_listening_action(db,p,'saveRule',{'name':'Jakarta monitoring','filters':{'query':'election','province':'DKI Jakarta','platforms':['tiktok']}})['rule']
    assert rule['name']=='Jakarta monitoring'
    r=social_listening_action(db,p,'runRule',{},id=rule['id'],provider_client=fake_provider)
    rid=r['results'][0]['id']
    social_listening_action(db,p,'review',{'decision':'RELEVANT'},id=rid)
    promoted=social_listening_action(db,p,'promote',{},id=rid)
    assert promoted['intelligence_code'].startswith('INT-')
    item=db.get(IntelligenceItem,int(promoted['intelligence_id']))
    assert item.ingestion_method=='SOCIALCRAWL'
    assert item.review_status=='Pending Review'
    assert item.verification_status=='UNVERIFIED'
    db.close()

def test_promotion_requires_prior_human_review():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'election','platforms':['tiktok']}},provider_client=fake_provider)
    rid=r['results'][0]['id']
    try:
        social_listening_action(db,p,'promote',{},id=rid)
        assert False, 'Expected discovered result promotion to be blocked'
    except ValueError as exc:
        assert 'Human review is required' in str(exc)
    social_listening_action(db,p,'review',{'decision':'NOT_RELEVANT','notes':'Outside monitoring scope'},id=rid)
    try:
        social_listening_action(db,p,'promote',{},id=rid)
        assert False, 'Expected not relevant result promotion to be blocked'
    except ValueError as exc:
        assert 'Human review is required' in str(exc)
    social_listening_action(db,p,'review',{'decision':'MONITOR'},id=rid)
    promoted=social_listening_action(db,p,'promote',{},id=rid)
    assert promoted['intelligence_code'].startswith('INT-')
    db.close()

def test_not_relevant_review_requires_notes_and_preserves_them():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'election','platforms':['tiktok']}},provider_client=fake_provider)
    rid=r['results'][0]['id']
    try:
        social_listening_action(db,p,'review',{'decision':'NOT_RELEVANT','notes':''},id=rid)
        assert False, 'Expected notes requirement'
    except ValueError as exc:
        assert 'Review notes are required' in str(exc)
    reviewed=social_listening_action(db,p,'review',{'decision':'NOT_RELEVANT','notes':'Duplicate or outside monitoring scope'},id=rid)
    assert reviewed['result']['review_state']=='NOT_RELEVANT'
    assert reviewed['result']['review_notes']=='Duplicate or outside monitoring scope'
    db.close()

def test_deduplication_prevents_repeat_imports():
    db=SessionLocal(); p=admin(db)
    a=social_listening_action(db,p,'search',{'filters':{'query':'election'}},provider_client=fake_provider)
    b=social_listening_action(db,p,'search',{'filters':{'query':'election'}},provider_client=fake_provider)
    assert len(a['results'])==2
    assert len(b['results'])==0
    assert db.query(SocialListeningResult).count()==2
    db.close()


def nested_provider(filters):
    return {'success':True,'request_id':'req-nested','credits_used':5,'credits_remaining':975,'cached':False,'data':{'items':[
      {'platform':'tiktok','post':{'id':'nested-1','url':'https://www.tiktok.com/@nested/video/1','author':{'display_name':'Nested Actor','username':'@nested'},'content':{'text':'Nested BAWASLU update','type':'video'},'engagement':{'views':3210,'likes':210,'comments':18,'shares':7},'published_at':'2026-10-07T04:00:00Z'},'computed':{'language':'id','engagement_rate':0.073,'estimated_reach':4100,'relevance':{'p':0.88}}}
    ]}}

def test_normalized_nested_socialcrawl_fields_are_preserved():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'BAWASLU','platforms':['tiktok']}},provider_client=nested_provider)
    x=r['results'][0]
    assert x['observed_handle']=='@nested'
    assert x['published_at']=='2026-10-07T04:00:00Z'
    assert x['language']=='id'
    assert x['relevance_score']=='0.88'
    assert x['engagement']['views']==3210
    assert x['engagement']['engagement_rate']==0.073
    assert x['content_type']=='video'
    db.close()


def source_items_provider(filters):
    return {'success':True,'request_id':'req-source-items','credits_used':5,'credits_remaining':970,'cached':False,'data':{'items':[
      {'platform':'tiktok-hashtag','id':'ranked-1','url':'https://www.tiktok.com/@politik.seputar/video/99','text':'BAWASLU source item test','computed':{'relevance':{'p':0.81}},'source_items':[{'author':'@politik.seputar','published_at':'2026-10-07T05:30:00Z','metadata':{'language':'id'},'engagement':{'views':9000,'likes':850,'comments':65,'shares':33,'engagement_rate':0.105}}]}
    ]}}

def test_source_items_metadata_fallbacks_are_preserved():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'BAWASLU','platforms':['tiktok']}},provider_client=source_items_provider)
    x=r['results'][0]
    assert x['observed_handle']=='@politik.seputar'
    assert x['published_at']=='2026-10-07T05:30:00Z'
    assert x['language']=='id'
    assert x['relevance_score']=='0.81'
    assert x['engagement']['views']==9000
    assert x['engagement']['engagement_rate']==0.105
    db.close()


def test_value_supports_list_indices_for_universal_search_source_items():
    from app.socialcrawl import _value
    row={'source_items':[{'published_at':'2026-10-07T05:30:00Z','metadata':{'language':'id'},'engagement':{'views':9000}}]}
    assert _value(row,'source_items.0.published_at')=='2026-10-07T05:30:00Z'
    assert _value(row,'source_items.0.metadata.language')=='id'
    assert _value(row,'source_items.0.engagement.views')==9000


def test_result_limit_is_enforced_after_filtering():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'election','limit':1}},provider_client=fake_provider)
    assert len(r['results'])==1
    assert r['run']['result_count']==1
    assert db.query(SocialListeningResult).count()==1
    db.close()


def test_cost_preflight_estimates_social_and_news_and_warns_on_repeat():
    from app.socialcrawl import estimate_search_cost
    social=estimate_search_cost({'query':'BAWASLU','platforms':['tiktok'],'limit':2})
    assert social['estimated_credits']==20
    assert social['result_limit_affects_cost'] is False
    mixed=estimate_search_cost({'query':'BAWASLU','platforms':['tiktok','online_news']})
    assert mixed['estimated_credits']==21
    news=estimate_search_cost({'query':'BAWASLU','platforms':['online_news']})
    assert news['estimated_credits']==1

    db=SessionLocal(); p=admin(db)
    social_listening_action(db,p,'search',{'filters':{'query':'BAWASLU','platforms':['tiktok']}},provider_client=fake_provider)
    pf=social_listening_action(db,p,'preflight',{'filters':{'query':'BAWASLU','platforms':['tiktok']}})
    assert pf['estimated_credits']==20
    assert pf['duplicate_recent'] is not None
    assert pf['duplicate_recent']['credits_used']==20
    db.close()

def test_default_social_listening_platforms_exclude_online_news():
    from app.socialcrawl import _normalize_filters
    f=_normalize_filters({'query':'BAWASLU'})
    assert 'online_news' not in f['platforms']
    assert 'tiktok' in f['platforms']

def test_usage_action_returns_summary_without_result_id():
    db=SessionLocal(); p=admin(db)
    social_listening_action(db,p,'search',{'filters':{'query':'election','platforms':['tiktok']}},provider_client=fake_provider)
    usage=social_listening_action(db,p,'usage',{})
    assert usage['summary']['last_24h_credits']==20
    assert usage['summary']['last_24h_calls']==1
    assert usage['usage'][0]['credits_used']==20
    assert usage['usage'][0]['user_name']=='Admin'
    db.close()


def test_review_queue_filters_states_and_never_calls_provider():
    db=SessionLocal(); p=admin(db)
    r=social_listening_action(db,p,'search',{'filters':{'query':'election','platforms':['tiktok']}},provider_client=fake_provider)
    first=r['results'][0]['id']
    social_listening_action(db,p,'review',{'decision':'MONITOR'},id=first)

    all_queue=social_listening_action(db,p,'queue',{})
    assert all_queue['counts']['ALL']==2
    assert all_queue['counts']['MONITOR']==1
    assert all_queue['counts']['DISCOVERED']==1

    monitor=social_listening_action(db,p,'queue',{'state':'MONITOR'})
    assert len(monitor['results'])==1
    assert monitor['results'][0]['review_state']=='MONITOR'
    assert db.query(SocialListeningProviderUsage).count()==1

    try:
        social_listening_action(db,p,'queue',{'state':'INVALID'})
        assert False, 'Expected invalid queue state to fail'
    except ValueError:
        pass
    db.close()

def test_social_listening_geography_is_restricted_to_authorized_scope():
    db=SessionLocal(); p=provincial_analyst(db,'Bali')
    options=social_listening_action(db,p,'filterOptions',{})
    assert [x['name'] for x in options['provinces']]==['Bali']
    assert options['regencies']
    assert all(str(x['province_code'])=='51' for x in options['regencies'])

    pf=social_listening_action(db,p,'preflight',{'filters':{'query':'BAWASLU','platforms':['online_news']}})
    assert pf['filters']['province']=='Bali'
    assert pf['estimated_credits']==1

    try:
        social_listening_action(db,p,'preflight',{'filters':{'query':'BAWASLU','province':'DKI Jakarta','platforms':['online_news']}})
        assert False, 'Expected out-of-scope province to be blocked'
    except PermissionError as exc:
        assert 'outside your authorized province' in str(exc)

    rule=social_listening_action(db,p,'saveRule',{'name':'Scoped Bali news','filters':{'query':'BAWASLU','platforms':['online_news']}})['rule']
    assert rule['filters']['province']=='Bali'
    db.close()

def test_social_listening_queue_and_review_are_geographically_scoped():
    db=SessionLocal()
    national=admin(db)
    bali=provincial_analyst(db,'Bali')

    bali_run=social_listening_action(db,bali,'search',{'filters':{'query':'bali election','platforms':['online_news']}},provider_client=fake_provider)
    bali_id=bali_run['results'][0]['id']

    jakarta_run=social_listening_action(db,national,'search',{'filters':{'query':'jakarta election','province':'DKI Jakarta','platforms':['online_news']}},provider_client=lambda f:{
      'success':True,'request_id':'req-jkt','credits_used':1,'credits_remaining':999,'cached':False,
      'data':{'items':[{'id':'jkt-1','platform':'online_news','url':'https://example.com/jakarta','title':'Jakarta election update','snippet':'Public Jakarta election administration update'}]}
    })
    jakarta_id=jakarta_run['results'][0]['id']

    queue=social_listening_action(db,bali,'queue',{})
    assert any(x['id']==bali_id for x in queue['results'])
    assert all(x['id']!=jakarta_id for x in queue['results'])

    try:
        social_listening_action(db,bali,'review',{'decision':'RELEVANT'},id=jakarta_id)
        assert False, 'Expected out-of-scope review to be blocked'
    except PermissionError as exc:
        assert 'outside your authorized geographic scope' in str(exc)

    reviewed=social_listening_action(db,bali,'review',{'decision':'RELEVANT'},id=bali_id)
    assert reviewed['result']['review_state']=='RELEVANT'
    db.close()

def test_saved_searches_are_owner_scoped_and_admin_can_manage_all():
    db=SessionLocal()
    national=admin(db)
    bali=provincial_analyst(db,'Bali')

    admin_rule=social_listening_action(db,national,'saveRule',{'name':'Admin monitoring','filters':{'query':'BAWASLU','platforms':['online_news']}})['rule']
    bali_rule=social_listening_action(db,bali,'saveRule',{'name':'Bali monitoring','filters':{'query':'BAWASLU Bali','platforms':['online_news']}})['rule']

    analyst_rules=social_listening_action(db,bali,'rules',{})['rules']
    assert [x['id'] for x in analyst_rules]==[bali_rule['id']]
    assert all(x['created_by']==bali['id'] for x in analyst_rules)

    admin_rules=social_listening_action(db,national,'rules',{})['rules']
    assert {x['id'] for x in admin_rules}=={admin_rule['id'],bali_rule['id']}

    try:
        social_listening_action(db,bali,'saveRule',{'name':'Hijack','filters':{'query':'other','platforms':['online_news']}},id=admin_rule['id'])
        assert False, 'Expected non-owner update to be blocked'
    except PermissionError as exc:
        assert 'owner or an administrator' in str(exc)

    try:
        social_listening_action(db,bali,'runRule',{},id=admin_rule['id'],provider_client=fake_provider)
        assert False, 'Expected non-owner run to be blocked'
    except PermissionError as exc:
        assert 'owner or an administrator' in str(exc)

    updated=social_listening_action(db,national,'saveRule',{'name':'Bali monitoring updated','filters':bali_rule['filters'],'enabled':True},id=bali_rule['id'])['rule']
    assert updated['name']=='Bali monitoring updated'
    db.close()

def test_saved_search_view_includes_creator_scope_and_manageability():
    db=SessionLocal()
    national=admin(db)
    bali=provincial_analyst(db,'Bali')
    created=social_listening_action(db,bali,'saveRule',{'name':'Bali creator metadata','filters':{'query':'BAWASLU Bali','platforms':['online_news']}})['rule']
    assert created['creator_name']=='Provincial Analyst'
    assert created['is_owner'] is True
    assert created['can_manage'] is True
    assert created['scope_label']=='Bali'

    admin_rules=social_listening_action(db,national,'rules',{})['rules']
    viewed=next(x for x in admin_rules if x['id']==created['id'])
    assert viewed['creator_name']=='Provincial Analyst'
    assert viewed['is_owner'] is False
    assert viewed['can_manage'] is True
    assert viewed['scope_label']=='Bali'
    db.close()
