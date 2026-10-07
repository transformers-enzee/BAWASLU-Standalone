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
