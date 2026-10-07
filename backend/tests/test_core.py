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


def test_source_retrieval_parser_extracts_article_metadata():
    from app.source_retrieval import _extract_html
    html='''<html lang="id-ID"><head><title>Fallback title</title><meta property="og:title" content="Judul Berita"><meta property="og:site_name" content="Media Test"><meta name="author" content="Reporter"><meta property="article:published_time" content="2026-10-07T09:15:00+07:00"><link rel="canonical" href="/news/1"></head><body><p>Paragraf berita yang cukup panjang untuk menjadi isi sumber asli yang disimpan oleh sistem.</p><p>Paragraf kedua memberikan konteks tambahan untuk pengujian ekstraksi artikel.</p></body></html>'''
    r=_extract_html(html,'https://example.com/path')
    assert r['title']=='Judul Berita'
    assert r['source_name']=='Media Test'
    assert r['author']=='Reporter'
    assert r['original_language_code']=='id'
    assert r['publication_date']=='2026-10-07'
    assert r['publication_time_precision']=='EXACT'
    assert r['canonical_url']=='https://example.com/news/1'
    assert 'Paragraf berita' in r['original_content']

def test_source_retrieval_blocks_private_addresses():
    from app.source_retrieval import _validate_public_url
    import pytest
    with pytest.raises(ValueError):
        _validate_public_url('http://127.0.0.1/private')
    with pytest.raises(ValueError):
        _validate_public_url('http://169.254.169.254/latest/meta-data')


def test_jsonld_article_metadata_and_content_are_preferred():
    from app.source_retrieval import _extract_html
    html='''<html lang="en"><head><title>Post - Muhammad Bobby Afif Nasution</title><meta property="og:title" content="Post - Muhammad Bobby Afif Nasution"><script type="application/ld+json">{"@context":"https://schema.org","@type":"NewsArticle","headline":"Muhammad Bobby Afif Nasution","author":{"@type":"Person","name":"Alumni IPB"},"publisher":{"@type":"Organization","name":"Alumni IPB Pedia"},"datePublished":"2026-09-18T10:45:00+07:00","inLanguage":"id-ID","url":"https://alumniipbpedia.id/post/muhammad-bobby-afif-nasution","articleBody":"Muhammad Bobby Afif Nasution lahir di Medan sebagai putra bungsu dari keluarga yang menjunjung pendidikan. Ia juga aktif dalam kegiatan masyarakat dan pembangunan untuk Sumatera Utara."}</script></head><body><p>Muhammad Bobby Afif Nasution lahir di Medan sebagai putra bungsu dari keluarga yang menjunjung pendidikan.</p></body></html>'''
    r=_extract_html(html,'https://alumniipbpedia.id/post/muhammad-bobby-afif-nasution')
    assert r['title']=='Muhammad Bobby Afif Nasution'
    assert r['author']=='Alumni IPB'
    assert r['source_name']=='Alumni IPB Pedia'
    assert r['platform']=='Web'
    assert r['original_language_code']=='id'
    assert r['publication_date']=='2026-09-18'
    assert r['publication_time_precision']=='EXACT'
    assert 'pembangunan untuk Sumatera Utara' in r['original_content']

def test_article_text_can_override_incorrect_html_language():
    from app.source_retrieval import _extract_html
    html='''<html lang="en"><head><title>Berita</title></head><body><p>Informasi ini adalah laporan pemilu yang disampaikan oleh Bawaslu dan telah diberikan kepada masyarakat untuk pengawasan.</p><p>Dalam laporan tersebut juga dijelaskan bahwa proses ini dilakukan dengan ketentuan yang berlaku.</p></body></html>'''
    r=_extract_html(html,'https://example.com/berita')
    assert r['original_language_code']=='id'


def test_visible_heading_and_indonesian_date_fallbacks():
    from app.source_retrieval import _extract_html
    html='''<html lang="id"><head><title>Post - Muhammad Bobby Afif Nasution</title><meta property="og:title" content="Post - Muhammad Bobby Afif Nasution"></head><body><div>Pencarian</div><h2>Muhammad Bobby Afif Nasution</h2><a>Admin</a><span>03 Maret 2026</span><span>0 Komentar</span><p>Membangun Sumatera Utara Melalui Kolaborasi dan Inovasi merupakan bagian dari profil ini.</p><p>Muhammad Bobby Afif Nasution lahir di Medan pada 5 Juli 1991 sebagai putra bungsu dari keluarga yang menjunjung nilai pendidikan.</p></body></html>'''
    r=_extract_html(html,'https://alumniipbpedia.id/post/muhammad-bobby-afif-nasution')
    assert r['title']=='Muhammad Bobby Afif Nasution'
    assert r['publication_date']=='2026-03-03'
    assert r['publication_time_precision']=='TIME_UNKNOWN'


def test_date_only_precision_contract_uses_time_unknown():
    from app.source_retrieval import _published_parts
    d,t,p=_published_parts('2026-03-03')
    assert d=='2026-03-03'
    assert t==''
    assert p=='TIME_UNKNOWN'


def test_near_duplicate_detection_uses_similarity_and_human_review():
    h=auth()
    first={'action':'create','data':{'title':'Bawaslu reviews election supervision access in Jakarta','original_content':'Bawaslu reviewed access to election supervision documents in Jakarta after officials reported restrictions during the verification process. The agency requested complete access for oversight and documented the incident for follow-up.','source_name':'Media Nusantara','platform':'Web','publication_date':'2026-10-07','source_url':'https://media.example/a','jurisdiction_type':'National','confirm_jurisdiction':True}}
    r=client.post('/api/functions/intelligence',json=first,headers=h); assert r.status_code==200
    original=r.json()['item']
    second={'action':'create','data':{'title':'Bawaslu reviews access for election supervision in Jakarta','original_content':'Officials said Bawaslu reviewed access to election supervision documents in Jakarta after restrictions were reported during verification. The agency requested complete access for oversight and recorded the incident for further follow-up.','source_name':'Media Nusantara','platform':'Web','publication_date':'2026-10-07','source_url':'https://media.example/b','jurisdiction_type':'National','confirm_jurisdiction':True}}
    r=client.post('/api/functions/intelligence',json=second,headers=h); assert r.status_code==200
    duplicate=r.json()['item']
    assert duplicate['duplicate_of']==original['id']
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':duplicate['id']},headers=h); assert r.status_code==200
    body=r.json(); assert isinstance(body['related'],list); assert isinstance(body['files'],list); assert isinstance(body['events'],list)
    match=body['duplicate_match']; assert isinstance(match['basis'],list)
    assert match['score']>=0.78
    assert 'Same source / publisher' in match['basis']
    assert r.json()['comparison']['id']==original['id']
    r=client.post('/api/functions/intelligence',json={'action':'duplicate','data':{'decision':'Keep Separate'},'id':duplicate['id']},headers=h); assert r.status_code==200
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':duplicate['id']},headers=h)
    assert r.json()['item']['duplicate_resolution']=='Keep Separate'

def test_unrelated_items_are_not_marked_duplicate():
    h=auth()
    a={'action':'create','data':{'title':'Bawaslu meeting in Jakarta','original_content':'Election supervisors discussed monitoring access and reporting procedures with local officials in Jakarta.','source_name':'Source A','source_url':'https://a.example/one','jurisdiction_type':'National','confirm_jurisdiction':True}}
    b={'action':'create','data':{'title':'Flood response in Surabaya','original_content':'Emergency teams distributed food and opened shelters after heavy rain affected several neighbourhoods.','source_name':'Source B','source_url':'https://b.example/two','jurisdiction_type':'National','confirm_jurisdiction':True}}
    client.post('/api/functions/intelligence',json=a,headers=h)
    r=client.post('/api/functions/intelligence',json=b,headers=h); assert r.status_code==200
    assert not r.json()['item']['duplicate_of']


def test_no_geographic_mismatch_contract_is_safe_for_frontend():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{'title':'No mismatch','original_content':'Evidence','jurisdiction_type':'National','confirm_jurisdiction':True}},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    assert r.status_code==200
    mismatch=r.json()['item']['geographic_mismatch']
    assert mismatch=={'status':'none'}


def test_existing_record_source_recovery_fills_only_missing_fields(monkeypatch):
    import app.domain as domain
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Existing headline',
      'original_content':'Existing original evidence must stay unchanged.',
      'source_type':'MANUAL_LINK',
      'source_url':'https://example.com/article',
      'source_name':'Existing Publisher',
      'platform':'Web',
      'author':'',
      'publication_time_precision':'UNKNOWN',
      'jurisdiction_type':'National',
      'confirm_jurisdiction':True
    }},headers=h)
    iid=r.json()['item']['id']
    monkeypatch.setattr(domain,'fetch_public_source',lambda url:{
      'available':True,
      'title':'Retrieved headline must not replace existing',
      'original_content':'Retrieved content must not replace existing',
      'source_name':'Retrieved Publisher',
      'platform':'Web',
      'author':'Reporter Name',
      'original_language_code':'id',
      'publication_date':'2026-10-06',
      'publication_time':'14:30:00',
      'publication_time_precision':'EXACT',
      'retrieval_status':'CONTENT_RETRIEVED'
    })
    r=client.post('/api/functions/intelligence',json={'action':'recoverSource','data':{'automatic':True},'id':iid},headers=h)
    assert r.status_code==200, r.text
    body=r.json()
    assert body['item']['title']=='Existing headline'
    assert body['item']['original_content']=='Existing original evidence must stay unchanged.'
    assert body['item']['source_name']=='Existing Publisher'
    assert body['item']['author']=='Reporter Name'
    assert body['item']['original_language_code']=='id'
    assert body['item']['publication_date']=='2026-10-06'
    assert body['item']['publication_time_precision']=='EXACT'
    assert body['item']['publication_datetime']=='2026-10-06T14:30:00'
    assert set(body['recovered_fields']) >= {'author','original_language_code','publication_date','publication_time_precision','publication_datetime'}

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    actions=[e['action'] for e in r.json()['events']]
    assert 'SOURCE_RECOVERED' in actions


def test_source_recovery_downgrades_exact_precision_without_time():
    from app.domain import apply_source_recovery
    item=IntelligenceItem(
      intelligence_id='INT-TEST-RECOVERY',
      title='Existing',
      original_content='Evidence',
      source_type='MANUAL_LINK',
      source_url='https://example.com/item',
      publication_time_precision='UNKNOWN'
    )
    changes,recovered=apply_source_recovery(item,{
      'publication_date':'2026-10-05',
      'publication_time':'',
      'publication_time_precision':'EXACT'
    })
    assert item.publication_date=='2026-10-05'
    assert item.publication_time_precision=='TIME_UNKNOWN'
    assert item.publication_datetime==''
    assert 'publication_date' in recovered
    assert 'publication_time_precision' in recovered


def test_profile_derives_region_codes_from_indonesian_names():
    db=SessionLocal()
    u=User(email='codes@test.local',full_name='Codes',password_hash=hash_password('secret')); db.add(u); db.flush()
    db.add(AccessGrant(user_id=u.id,access_role='Provincial Analyst',geographic_scope='Province',province='Jawa Barat',permissions_json=json.dumps(default_permissions('Provincial Analyst')),status='Active')); db.commit()
    p=profile(db,u)
    assert p['province_code']=='32'
    db.close()

def test_multi_region_acl_enforces_assignments_for_regional_users():
    db=SessionLocal()
    multi=IntelligenceItem(
      intelligence_id='INT-2026-MULTI01',title='Multi region',
      jurisdiction_type='Multi-Region',jurisdiction_confirmed=True,
      geographic_assignments_json=json.dumps([
        {'province_code':'32','province':'West Java','regency_city_code':'32.73','regency_city':'Kota Bandung'},
        {'province_code':'31','province':'DKI Jakarta','regency_city_code':'','regency_city':''}
      ])
    )
    db.add(multi)
    p_user=User(email='westjava@test.local',full_name='West Java',password_hash=hash_password('secret')); db.add(p_user); db.flush()
    db.add(AccessGrant(user_id=p_user.id,access_role='Provincial Analyst',geographic_scope='Province',province='Jawa Barat',permissions_json=json.dumps(default_permissions('Provincial Analyst')),status='Active'))
    c_user=User(email='bandung@test.local',full_name='Bandung',password_hash=hash_password('secret')); db.add(c_user); db.flush()
    db.add(AccessGrant(user_id=c_user.id,access_role='Regency/City Analyst',geographic_scope='Regency/City',province='Jawa Barat',regency_city='Kota Bandung',permissions_json=json.dumps(default_permissions('Regency/City Analyst')),status='Active'))
    other=User(email='bogor@test.local',full_name='Bogor',password_hash=hash_password('secret')); db.add(other); db.flush()
    db.add(AccessGrant(user_id=other.id,access_role='Regency/City Analyst',geographic_scope='Regency/City',province='Jawa Barat',regency_city='Kota Bogor',permissions_json=json.dumps(default_permissions('Regency/City Analyst')),status='Active'))
    db.commit()
    assert allowed(profile(db,p_user),multi) is True
    assert allowed(profile(db,c_user),multi) is True
    assert allowed(profile(db,other),multi) is False
    db.close()

def test_multi_region_create_normalizes_names_and_requires_two_distinct_areas():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Cross-region monitoring',
      'original_content':'Evidence across two regions.',
      'jurisdiction_type':'Multi-Region',
      'geographic_assignments':[
        {'province_code':'32','regency_city_code':'32.73'},
        {'province_code':'31','regency_city_code':''}
      ],
      'confirm_jurisdiction':True
    }},headers=h)
    assert r.status_code==200, r.text
    item=r.json()['item']
    assert item['jurisdiction_type']=='Multi-Region'
    assert len(item['geographic_assignments'])==2
    assert item['geographic_assignments'][0]['province']
    assert item['geographic_assignments'][0]['regency_city']=='Kota Bandung'

    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Invalid multi',
      'original_content':'Only one unique area.',
      'jurisdiction_type':'Multi-Region',
      'geographic_assignments':[
        {'province_code':'32','regency_city_code':'32.73'},
        {'province_code':'32','regency_city_code':'32.73'}
      ],
      'confirm_jurisdiction':True
    }},headers=h)
    assert r.status_code==400
