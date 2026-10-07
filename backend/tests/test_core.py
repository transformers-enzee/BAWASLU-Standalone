import json, os, tempfile
os.environ['DATABASE_URL']='sqlite:///:memory:'
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, SessionLocal
from app.models import User, AccessGrant, IntelligenceItem, WatchlistItem, SourceAccount
from app.auth import hash_password
from app.access import default_permissions, profile, allowed

client=TestClient(app)

def setup_function():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db=SessionLocal()
    u=User(email='admin@test.local',full_name='Admin',password_hash=hash_password('secret'),platform_admin=True); db.add(u); db.flush()
    db.add(AccessGrant(user_id=u.id,access_role='National Administrator',geographic_scope='Nationwide',permissions_json=json.dumps(default_permissions('National Administrator')),status='Active')); db.commit(); db.close()

def auth():
    r=client.post('/api/auth/login',json={'email':'admin@test.local','password':'secret'}); assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_health():
    r=client.get('/api/health'); assert r.status_code==200; assert r.json()['product']=='bawaslu'

def test_create_and_list_intelligence_preserves_source_identity_fields():
    h=auth()
    payload={'action':'create','data':{'title':'Test item','original_content':'Evidence text','source_type':'MANUAL_LINK','source_url':'https://www.tiktok.com/@publisher/video/1','platform':'TikTok','jurisdiction_type':'Province','province':'Jawa Barat','confirm_jurisdiction':True}}
    r=client.post('/api/functions/intelligence',json=payload,headers=h); assert r.status_code==200, r.text
    item=r.json()['item']; assert item['intelligence_id'].startswith('INT-'); assert item['observed_publisher_handle']=='@publisher'; assert item['source_identity']['status']=='KNOWN_EXTERNAL_ACCOUNT'; assert item['jurisdiction_confirmed'] is True
    r=client.post('/api/functions/intelligence',json={'action':'list','data':{}},headers=h); assert len(r.json()['items'])==1

def test_registered_source_account_resolves_identity():
    db=SessionLocal(); w=WatchlistItem(name='Actor',type='Candidate',province='',regency_city=''); db.add(w); db.flush(); db.add(SourceAccount(watchlist_id=w.id,platform='TikTok',url='https://www.tiktok.com/@actor',handle='@actor')); db.commit(); db.close()
    h=auth(); r=client.post('/api/functions/intelligence',json={'action':'resolveSourceIdentity','data':{'source_url':'https://www.tiktok.com/@actor/video/123'}},headers=h); assert r.status_code==200; assert r.json()['source_identity']['status']=='REGISTERED_ACCOUNT_CONFIRMED'

def test_geographic_acl_is_server_side():
    db=SessionLocal(); u=User(email='prov@test.local',full_name='Prov',password_hash=hash_password('secret')); db.add(u); db.flush(); perms=default_permissions('Provincial Analyst'); db.add(AccessGrant(user_id=u.id,access_role='Provincial Analyst',geographic_scope='Province',province='Jawa Barat',permissions_json=json.dumps(perms),status='Active')); db.add(IntelligenceItem(intelligence_id='INT-2026-000001',title='Visible',province='Jawa Barat',jurisdiction_type='Province',jurisdiction_confirmed=True)); db.add(IntelligenceItem(intelligence_id='INT-2026-000002',title='Hidden',province='Jawa Tengah',jurisdiction_type='Province',jurisdiction_confirmed=True)); db.commit(); db.close()
    r=client.post('/api/auth/login',json={'email':'prov@test.local','password':'secret'}); h={'Authorization':'Bearer '+r.json()['access_token']}
    r=client.post('/api/functions/intelligence',json={'action':'list','data':{}},headers=h); assert [x['title'] for x in r.json()['items']]==['Visible']

def test_human_verification_is_separate_action():
    h=auth(); r=client.post('/api/functions/intelligence',json={'action':'create','data':{'title':'Evidence','original_content':'x','jurisdiction_type':'National','confirm_jurisdiction':True}},headers=h); iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'verifyEvidence','data':{},'id':iid},headers=h); assert r.status_code==200
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h); assert r.json()['item']['verification_status']=='HUMAN_VERIFIED'; assert r.json()['item']['evidence_state']=='VERIFIED'
