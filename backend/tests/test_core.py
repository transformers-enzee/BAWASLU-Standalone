import json, os, tempfile
os.environ['DATABASE_URL']='sqlite:///:memory:'
os.environ.pop('OPENAI_API_KEY',None)
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


def test_social_page_partial_retrieval_is_not_submission_ready():
    from app.source_retrieval import _extract_html, _social_platform
    html='''<html><head><title>TikTok - Make Your Day</title><meta property="og:title" content="TikTok"></head><body><div>Log in to TikTok</div></body></html>'''
    r=_extract_html(html,'https://www.tiktok.com/@example/video/123')
    assert r['available'] is True
    assert r['submission_ready'] is False
    assert _social_platform('https://www.tiktok.com/@example/video/123')=='TikTok'

def test_social_platform_detection_covers_supported_manual_urls():
    from app.source_retrieval import _social_platform
    assert _social_platform('https://www.instagram.com/p/abc')=='Instagram'
    assert _social_platform('https://youtu.be/abc')=='YouTube'
    assert _social_platform('https://x.com/example/status/1')=='X'
    assert _social_platform('https://www.reddit.com/r/test/comments/1')=='Reddit'


def test_generic_social_shell_titles_are_rejected_as_headlines():
    from app.source_retrieval import _generic_social_title
    assert _generic_social_title('TikTok - Make Your Day','TikTok') is True
    assert _generic_social_title('TikTok','TikTok') is True
    assert _generic_social_title('Actual election monitoring update from Bawaslu','TikTok') is False
    assert _generic_social_title('Login • Instagram','Instagram') is True


def test_tiktok_oembed_autofills_caption_and_identity():
    from app.source_retrieval import _apply_tiktok_oembed
    class Response:
        status_code=200
        content=b'{}'
        def json(self):
            return {'title':'Bawaslu mengawasi proses pemilu dan meminta masyarakat melaporkan dugaan pelanggaran. #Bawaslu #Pemilu','author_name':'Langkah Bobby'}
    class Client:
        def get(self,*args,**kwargs): return Response()
    result={'title':'','original_content':'','source_name':'tiktok.com','platform':'TikTok','author':'','original_language_code':''}
    out=_apply_tiktok_oembed(Client(),'https://www.tiktok.com/@langkahbobbynst/video/7691197405810674964',result)
    assert out['title']=='Bawaslu mengawasi proses pemilu dan meminta masyarakat melaporkan dugaan pelanggaran'
    assert out['original_content'].startswith('Bawaslu mengawasi proses pemilu')
    assert out['source_name']=='@langkahbobbynst'
    assert out['author']=='Langkah Bobby'
    assert out['platform']=='TikTok'
    assert out['original_language_code']=='id'
    assert out['oembed_used'] is True


def test_tiktok_caption_headline_is_first_clean_sentence_and_language_overrides_shell():
    from app.source_retrieval import _apply_tiktok_oembed
    caption='Pada 2026, fasilitas listrik dan internet di seluruh SMA, SMK, dan SLB Negeri di bawah kewenangan Pemprov Sumut telah terpenuhi 100%. Program ini ditujukan untuk mendukung pembelajaran digital, termasuk bagi sekolah di wilayah yang sulit dijangkau. #PendidikanSumut'
    class Response:
        status_code=200
        content=b'{}'
        def json(self):
            return {'title':caption,'author_name':'Langkah Bobby'}
    class Client:
        def get(self,*args,**kwargs): return Response()
    result={'title':'TikTok - Make Your Day','original_content':'','source_name':'tiktok.com','platform':'TikTok','author':'','original_language_code':'en'}
    out=_apply_tiktok_oembed(Client(),'https://www.tiktok.com/@langkahbobbynst/video/7691197405810674964',result)
    assert out['title']=='Pada 2026, fasilitas listrik dan internet di seluruh SMA, SMK, dan SLB Negeri di bawah kewenangan Pemprov Sumut telah terpenuhi 100%'
    assert out['original_content']==caption
    assert out['original_language_code']=='id'

def test_caption_headline_caps_long_caption_without_copying_everything():
    from app.source_retrieval import _caption_headline
    caption=' '.join(['kata']*80)
    headline=_caption_headline(caption,80)
    assert len(headline)<=81
    assert headline.endswith('…')


def test_geographic_mismatch_blocks_final_validation_until_human_resolution():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Geographic mismatch case',
      'original_content':'Source evidence refers to Jakarta while the submitted jurisdiction is West Java.',
      'jurisdiction_type':'Province','province_code':'32','confirm_jurisdiction':True,
      'proposed_geography':{'jurisdiction_type':'Province','province_code':'31','supporting_text':'Source explicitly mentions Jakarta.'}
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    mismatch=r.json()['item']['geographic_mismatch']
    assert mismatch['status']=='pending'
    assert mismatch['fingerprint']

    r=client.post('/api/functions/intelligence',json={'action':'review','data':{'decision':'Validated as Relevant Intelligence','review_notes':'Final'},'id':iid},headers=h)
    assert r.status_code==400
    assert 'GEOGRAPHIC MISMATCH' in r.text

    r=client.post('/api/functions/intelligence',json={'action':'reviewGeographicMismatch','data':{'decision':'KEEP_CONFIRMED_JURISDICTION','reason':'Analyst confirms West Java assignment after checking the source.'},'id':iid},headers=h)
    assert r.status_code==200, r.text

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    resolved=r.json()['item']['geographic_mismatch']
    assert resolved['status']=='resolved'
    assert resolved['decision']=='KEEP_CONFIRMED_JURISDICTION'
    assert resolved['fingerprint']==mismatch['fingerprint']

    r=client.post('/api/functions/intelligence',json={'action':'review','data':{'decision':'Validated as Relevant Intelligence','review_notes':'Final after geography review'},'id':iid},headers=h)
    assert r.status_code==200, r.text

def test_geographic_mismatch_change_jurisdiction_updates_codes_and_audit():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Change jurisdiction case','original_content':'Source evidence points to Jakarta.',
      'jurisdiction_type':'Province','province_code':'32','confirm_jurisdiction':True,
      'proposed_geography':{'jurisdiction_type':'Province','province_code':'31','supporting_text':'Jakarta is explicitly named.'}
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'reviewGeographicMismatch','data':{'decision':'CHANGE_JURISDICTION','reason':'Source location verified as Jakarta.'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    body=r.json()
    assert body['item']['province_code']=='31'
    assert body['item']['jurisdiction_source']=='GEOGRAPHIC_MISMATCH_REVIEW'
    assert body['item']['geographic_mismatch']['status']=='resolved'
    actions=[e['action'] for e in body['events']]
    assert 'GEOGRAPHIC_MISMATCH_REVIEWED' in actions


def test_final_validation_is_blocked_until_all_generated_ai_suggestions_are_decided():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Triage governance case',
      'original_content':'Source material for triage governance testing with sufficient detail.',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{
        '_version':3,
        'summary':'AI proposed summary',
        'priority':'High',
        'issue_category':'Election administration'
      }
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    triage=r.json()['item']['triage_review']
    assert triage['generated'] is True
    assert triage['state']=='NOT STARTED'
    assert triage['total']==3

    r=client.post('/api/functions/intelligence',json={'action':'review','data':{'decision':'Validated as Relevant Intelligence','review_notes':'Attempt too early'},'id':iid},headers=h)
    assert r.status_code==400
    assert 'AI TRIAGE REVIEW INCOMPLETE' in r.text

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Accepted'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    assert r.json()['triage_review']['state']=='IN REVIEW'

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'priority','status':'Human Modified','value':'Medium'},'id':iid},headers=h)
    assert r.status_code==200, r.text

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'issue_category','status':'Human Rejected','reason':'Not supported by the source evidence.'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    assert r.json()['triage_review']['state']=='REVIEW COMPLETE'

    r=client.post('/api/functions/intelligence',json={'action':'review','data':{'decision':'Validated as Relevant Intelligence','review_notes':'All AI suggestions reviewed by human.'},'id':iid},headers=h)
    assert r.status_code==200, r.text

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    body=r.json()
    assert body['item']['review_status']=='Validated as Relevant Intelligence'
    assert body['item']['triage_review']['state']=='REVIEW COMPLETE'
    actions=[e['action'] for e in body['events']]
    assert actions.count('AI_SUGGESTION_DECIDED')==3

def test_triage_decision_rejects_unknown_key_and_empty_modified_value():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Triage validation case','original_content':'Evidence',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{'_version':3,'summary':'Suggested summary'}
    }},headers=h)
    iid=r.json()['item']['id']

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'confidence','status':'Human Accepted'},'id':iid},headers=h)
    assert r.status_code==400

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Modified','value':'   '},'id':iid},headers=h)
    assert r.status_code==400

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Rejected','reason':'no'},'id':iid},headers=h)
    assert r.status_code==400

def test_legacy_incomplete_triage_cannot_be_treated_as_review_complete():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Legacy triage case','original_content':'Evidence',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{'_decisions':{'legacy_field':{'status':'Human Accepted'}}}
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    triage=r.json()['item']['triage_review']
    assert triage['legacy'] is True
    assert triage['state']=='IN REVIEW'
    r=client.post('/api/functions/intelligence',json={'action':'review','data':{'decision':'Validated as Relevant Intelligence'},'id':iid},headers=h)
    assert r.status_code==400


def test_local_triage_generator_produces_valid_v3_contract():
    from app.domain import _valid_v3_proposal
    h=auth()
    content='Bawaslu memantau proses pemilu dan menerima laporan masyarakat. Informasi ini disimpan sebagai bahan pemantauan awal dan belum merupakan temuan atau pelanggaran.'
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Local V3 triage test',
      'original_content':content,
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'priority':'Medium','evidence_type':'OBSERVED'
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']

    r=client.post('/api/functions/intelligence',json={'action':'runTriage','data':{},'id':iid},headers=h)
    assert r.status_code==200, r.text
    body=r.json()
    proposal=body['suggestions']
    assert _valid_v3_proposal(proposal) is True
    assert proposal['_version']==3
    assert proposal['supervision_signal']=='NO SIGNAL IDENTIFIED'
    assert proposal['screening_confidence']=='LOW'
    assert proposal['confidence']=='LOW'
    assert proposal['evidence_type']=='OBSERVED'
    assert proposal['source_facts'].startswith('Bawaslu memantau')
    assert 'analysis' not in proposal
    assert body['generation']['generator']=='standalone-local-placeholder'
    assert body['generation']['validation_outcome']=='VALID_V3_PLACEHOLDER'
    assert body['triage_review']['state']=='NOT STARTED'
    assert body['triage_review']['total']>=5

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    item=r.json()['item']
    assert item['triage_review']['state']=='NOT STARTED'
    assert item['ai_suggestions']['_version']==3

def test_local_triage_contract_rejects_previous_incomplete_shape():
    from app.domain import _valid_v3_proposal
    old={'_version':3,'summary':'Old incomplete proposal','analysis':'Legacy field','confidence':'','priority':'Medium'}
    assert _valid_v3_proposal(old) is False

def test_local_triage_requires_original_source_content():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Missing source content',
      'original_content':'',
      'jurisdiction_type':'National','confirm_jurisdiction':True
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'runTriage','data':{},'id':iid},headers=h)
    assert r.status_code==400
    assert 'Original source content is required' in r.text


def test_human_approved_triage_projection_excludes_rejected_and_uses_modified_values():
    h=auth()
    suggestions={
      '_version':3,
      'summary':'AI summary',
      'actors':json.dumps([{'entity_id':'','entity_name':'Actor A','entity_type':'Person','relationship_to_content':'mentioned','evidence_basis':'Source names Actor A','evidence_type':'OBSERVED','confidence':'MEDIUM'}]),
      'supervision_signal':'MONITOR',
      'signal_reason':'AI reason',
      'priority':'High'
    }
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Human approved projection','original_content':'Source evidence.',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':suggestions
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']

    for payload in [
      {'key':'summary','status':'Human Modified','value':'Human corrected summary'},
      {'key':'actors','status':'Human Accepted'},
      {'key':'supervision_signal','status':'Human Accepted'},
      {'key':'signal_reason','status':'Human Rejected','reason':'Reason is not supported by the source.'},
      {'key':'priority','status':'Human Modified','value':'Medium'}
    ]:
        r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':payload,'id':iid},headers=h)
        assert r.status_code==200, r.text

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    approved=r.json()['item']['human_approved_triage']
    assert approved['values']['summary']=='Human corrected summary'
    assert approved['values']['actors'][0]['entity_name']=='Actor A'
    assert approved['values']['supervision_signal']=='MONITOR'
    assert approved['values']['priority']=='Medium'
    assert 'signal_reason' not in approved['values']
    assert 'signal_reason' in approved['rejected_fields']
    assert approved['provenance']['summary']['decision']=='Human Modified'
    assert approved['provenance']['actors']['decision']=='Human Accepted'
    assert approved['approved_count']==4

def test_changing_triage_decision_updates_human_approved_projection_without_overwriting_source():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Projection changes','original_content':'Original evidence stays unchanged.',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{'_version':3,'summary':'AI proposed summary'}
    }},headers=h)
    iid=r.json()['item']['id']

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Accepted'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    assert r.json()['human_approved_triage']['values']['summary']=='AI proposed summary'

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Rejected','reason':'Source does not support this summary.'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    assert 'summary' not in r.json()['human_approved_triage']['values']

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    item=r.json()['item']
    assert item['original_content']=='Original evidence stays unchanged.'
    assert item['ai_suggestions']['summary']=='AI proposed summary'
    assert 'summary' not in item['human_approved_triage']['values']

def test_final_review_audit_contains_human_approved_triage_snapshot():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Audit approved projection','original_content':'Evidence',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{'_version':3,'summary':'AI summary'}
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Accepted'},'id':iid},headers=h)
    assert r.status_code==200
    r=client.post('/api/functions/intelligence',json={'action':'review','data':{'decision':'Validated as Relevant Intelligence','review_notes':'Approved after triage review.'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    reviewed=[e for e in r.json()['events'] if e['action']=='REVIEWED'][0]
    snapshot=reviewed['changes']['human_approved_triage']['new']
    assert snapshot['values']['summary']=='AI summary'
    assert snapshot['provenance']['summary']['reviewer']=='Admin'


def test_human_approved_projection_exposes_rejected_pending_and_approved_field_states():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Field state clarity','original_content':'Source evidence.',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{
        '_version':3,
        'summary':'AI summary',
        'supervision_signal':'NO SIGNAL IDENTIFIED',
        'screening_confidence':'LOW',
        'priority':'Medium',
        'evidence_type':'OBSERVED'
      }
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']

    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Accepted'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'supervision_signal','status':'Human Rejected','reason':'No supported supervision signal.'},'id':iid},headers=h)
    assert r.status_code==200, r.text

    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    projection=r.json()['item']['human_approved_triage']
    assert projection['field_states']['summary']['state']=='APPROVED'
    assert projection['field_states']['summary']['decision']=='Human Accepted'
    assert projection['field_states']['supervision_signal']['state']=='REJECTED'
    assert projection['field_states']['supervision_signal']['reason']=='No supported supervision signal.'
    assert projection['field_states']['screening_confidence']['state']=='PENDING'
    assert projection['field_states']['evidence_type']['state']=='PENDING'
    assert 'supervision_signal' not in projection['values']
    assert projection['values']['summary']=='AI summary'

def test_projection_only_marks_generated_reviewable_fields_as_pending():
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Only proposed fields pending','original_content':'Evidence',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{'_version':3,'summary':'Only summary proposed'}
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    projection=r.json()['item']['human_approved_triage']
    assert projection['field_states']['summary']['state']=='PENDING'
    assert 'evidence_type' not in projection['field_states']
    assert projection['reviewable_fields']==['summary']


def test_openai_converter_produces_valid_v3_contract():
    from app.openai_triage import convert_model_result_to_v3
    from app.domain import _valid_v3_proposal
    result={
      'summary':'Bawaslu memantau tahapan pemilu.',
      'english_translation':'BAWASLU monitors the election stages.',
      'content_type':'News report',
      'activity':{'type':'Monitoring','description':'Election supervision activity','evidence_basis':'Source states Bawaslu is monitoring the process.','evidence_type':'OBSERVED','confidence':'HIGH'},
      'actors':[{'entity_id':'','entity_name':'Bawaslu','entity_type':'Institution','relationship_to_content':'supervisory body','evidence_basis':'Bawaslu is named in the source.','evidence_type':'OBSERVED','confidence':'HIGH'}],
      'location_signal':None,
      'narrative':None,
      'relationships':[],
      'topics':['election supervision'],
      'evidence_gaps':['No independent corroboration supplied'],
      'inferences':[],
      'check_next':[],
      'screening_evidence_basis':[],
      'supervision_signal':'NO SIGNAL IDENTIFIED',
      'signal_reason':'',
      'screening_confidence':'MEDIUM',
      'priority':'Medium',
      'evidence_type':'OBSERVED',
      'confidence':'HIGH'
    }
    proposal=convert_model_result_to_v3(result,'run-test','Sumber asli untuk pengujian.')
    assert _valid_v3_proposal(proposal) is True
    assert proposal['_version']==3
    assert proposal['actors'].startswith('[')
    assert proposal['relationships']==''
    assert proposal['source_facts']=='Sumber asli untuk pengujian.'

def test_run_triage_uses_production_provider_when_configured(monkeypatch):
    import app.domain as domain
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    def fake_generate(item,run_id,**kwargs):
        proposal=domain._local_v3_triage(item,run_id)
        proposal['summary']='Production structured summary'
        proposal['content_type']='News report'
        return proposal,{'model':'gpt-test-production','response_id':'resp_test','usage':{'input_tokens':100,'output_tokens':50,'total_tokens':150}}
    monkeypatch.setattr(domain,'generate_openai_triage',fake_generate)
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Production triage test','original_content':'Source material with enough information to test a production provider path.',
      'jurisdiction_type':'National','confirm_jurisdiction':True
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'runTriage','data':{},'id':iid},headers=h)
    assert r.status_code==200, r.text
    body=r.json()
    assert body['generation']['generator']=='openai-responses'
    assert body['generation']['generator_version']=='gpt-test-production'
    assert body['generation']['validation_outcome']=='VALID_V3_OPENAI'
    assert body['generation']['provider_response_id']=='resp_test'
    assert body['generation']['usage']['total_tokens']==150
    assert body['suggestions']['summary']=='Production structured summary'
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    assert r.json()['generation']['generator']=='openai-responses'
    assert r.json()['generation']['validation_outcome']=='VALID_V3_OPENAI'

def test_run_triage_falls_back_once_when_openai_provider_fails(monkeypatch):
    import app.domain as domain
    from app.openai_triage import OpenAITriageError
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    calls={'count':0}
    def fail_generate(item,run_id,**kwargs):
        calls['count']+=1
        raise OpenAITriageError('provider_timeout','timeout')
    monkeypatch.setattr(domain,'generate_openai_triage',fail_generate)
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Provider fallback test','original_content':'Source material used to confirm safe local fallback after a provider error.',
      'jurisdiction_type':'National','confirm_jurisdiction':True
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'runTriage','data':{},'id':iid},headers=h)
    assert r.status_code==200, r.text
    body=r.json()
    assert calls['count']==1
    assert body['generation']['generator']=='standalone-local-fallback'
    assert body['generation']['validation_outcome']=='FALLBACK_PROVIDER'
    assert body['generation']['fallback_code']=='provider_timeout'
    assert body['triage_review']['state']=='NOT STARTED'


def test_malay_and_indonesian_language_detection_are_distinguished():
    from app.source_retrieval import _language_detection
    malay='Pihak berkuasa memaklumkan kejadian itu berlaku selepas seorang kakitangan dilaporkan meninggal dunia. Setakat ini tiada penularan dikesan dan orang ramai diminta bertenang. Langkah berjaga-jaga turut dilaksanakan.'
    indonesian='Informasi ini adalah laporan pemilu yang disampaikan kepada masyarakat. Dalam laporan tersebut dijelaskan bahwa pengawasan dilakukan sesuai ketentuan yang berlaku dan Bawaslu meminta masyarakat melapor.'
    assert _language_detection(malay,'')['code']=='ms'
    assert _language_detection(indonesian,'en')['code']=='id'

def test_article_cleaner_removes_trailing_publisher_promotions():
    from app.source_retrieval import _extract_html
    html='''<html lang="ms"><head><title>Insiden makmal disiasat</title></head><body><p>Pihak berkuasa sedang menyiasat satu insiden selepas kemalangan makmal.</p><p>Setakat ini jenis patogen masih belum disahkan dan siasatan lanjut diteruskan.</p><p>Orang ramai diminta bertenang sementara kontak rapat dipantau.</p><p>Berita, sorotan utama, dan segala dari Awani terus ke peti masuk anda.</p><p>© 2026 Astro AWANI Network Sdn. Bhd. All Rights Reserved.</p><p>Dapatkan berita hari ini dan berita terkini Malaysia, Dunia, Sukan dan Hiburan.</p></body></html>'''
    r=_extract_html(html,'https://www.astroawani.com/berita-dunia/test')
    assert 'Dapatkan berita hari ini' not in r['original_content']
    assert 'Dapatkan berita hari ini' in r['raw_original_content']
    assert r['source_cleaning']['applied'] is True
    assert r['original_language_code']=='ms'

def test_run_triage_passes_cleaned_source_and_resolved_language(monkeypatch):
    import app.domain as domain
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    captured={}
    def fake_clean_generate(item,run_id,**kwargs):
        captured.update(kwargs)
        proposal=domain._local_v3_triage(item,run_id,source_text=kwargs.get('source_text'))
        return proposal,{'model':'gpt-test','response_id':'resp_clean','usage':{'input_tokens':50,'output_tokens':20,'total_tokens':70}}
    monkeypatch.setattr(domain,'generate_openai_triage',fake_clean_generate)
    text='''Pihak berkuasa memaklumkan satu kejadian sedang disiasat selepas laporan diterima.

Setakat ini tiada penularan dikesan dan orang ramai diminta bertenang.

Langkah berjaga-jaga turut dilaksanakan oleh pihak berkuasa.

Berita, sorotan utama, dan segala dari Awani terus ke peti masuk anda.

© 2026 Astro AWANI Network Sdn. Bhd. All Rights Reserved.

Dapatkan berita hari ini dan berita terkini Malaysia, Dunia, Sukan dan Hiburan.'''
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{'title':'Clean triage input','original_content':text,'jurisdiction_type':'National','confirm_jurisdiction':True}},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'runTriage','data':{},'id':iid},headers=h)
    assert r.status_code==200, r.text
    assert 'Dapatkan berita hari ini' not in captured['source_text']
    assert captured['language_code']=='ms'
    assert r.json()['generation']['source_cleaning']['applied'] is True
    assert r.json()['generation']['language_resolution']['code']=='ms'


def test_suggest_source_language_api_uses_shared_detector():
    h=auth()
    malay='Pihak berkuasa memaklumkan kejadian berlaku selepas laporan diterima. Setakat ini tiada penularan dikesan dan orang ramai diminta bertenang.'
    indonesian='Informasi ini adalah laporan pemilu yang disampaikan kepada masyarakat. Dalam laporan tersebut dijelaskan bahwa pengawasan dilakukan sesuai ketentuan yang berlaku.'
    english='Authorities reported that the investigation remains ongoing and the situation is stable. The source is a news report with no election activity.'
    r=client.post('/api/functions/suggestSourceLanguage',json={'content':malay},headers=h)
    assert r.status_code==200, r.text
    assert r.json()['language_code']=='ms'
    assert r.json()['language_label']=='Bahasa Melayu'
    r=client.post('/api/functions/suggestSourceLanguage',json={'content':indonesian},headers=h)
    assert r.status_code==200, r.text
    assert r.json()['language_code']=='id'
    r=client.post('/api/functions/suggestSourceLanguage',json={'content':english},headers=h)
    assert r.status_code==200, r.text
    assert r.json()['language_code']=='en'


def test_analyst_language_override_remains_authoritative():
    h=auth()
    malay='Pihak berkuasa memaklumkan kejadian berlaku selepas laporan diterima. Setakat ini tiada penularan dikesan dan orang ramai diminta bertenang.'
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Analyst language override','original_content':malay,'original_language_code':'id',
      'provider_source_metadata':{'language_selection_source':'ANALYST','language_selection_code':'id'},
      'jurisdiction_type':'National','confirm_jurisdiction':True
    }},headers=h)
    assert r.status_code==200, r.text
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'get','data':{},'id':iid},headers=h)
    assert r.status_code==200, r.text
    resolution=r.json()['item']['language_resolution']
    assert resolution['code']=='id'
    assert resolution['method']=='ANALYST_CONFIRMED'
    assert resolution['mismatch'] is True


def test_intelligence_assistant_respects_geographic_acl(monkeypatch):
    db=SessionLocal()
    u=User(email='assistant-prov@test.local',full_name='Assistant Provincial',password_hash=hash_password('secret'))
    db.add(u); db.flush()
    perms=default_permissions('Provincial Analyst')
    db.add(AccessGrant(user_id=u.id,access_role='Provincial Analyst',geographic_scope='Province',province='Jawa Barat',permissions_json=json.dumps(perms),status='Active'))
    db.add(IntelligenceItem(intelligence_id='INT-2026-100001',title='Visible Bandung election supervision',original_content='Bawaslu reviewed election supervision in Bandung.',province='Jawa Barat',jurisdiction_type='Province',jurisdiction_confirmed=True,priority='High',review_status='Validated as Relevant Intelligence',verification_status='HUMAN_VERIFIED',evidence_type='OBSERVED'))
    db.add(IntelligenceItem(intelligence_id='INT-2026-100002',title='Hidden Central Java record',original_content='Confidential Central Java election material.',province='Jawa Tengah',jurisdiction_type='Province',jurisdiction_confirmed=True,priority='High'))
    db.commit(); db.close()
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    r=client.post('/api/auth/login',json={'email':'assistant-prov@test.local','password':'secret'})
    h={'Authorization':'Bearer '+r.json()['access_token']}
    r=client.post('/api/functions/intelligenceAssistant',json={'question':'What election supervision records are available?'},headers=h)
    assert r.status_code==200, r.text
    body=r.json()
    ids=[x['intelligence_id'] for x in body['records']]
    assert 'INT-2026-100001' in ids
    assert 'INT-2026-100002' not in ids
    assert body['grounding']['scope']=='CURRENT_USER_AUTHORIZED_RECORDS_ONLY'

def test_intelligence_assistant_provider_receives_only_human_approved_triage(monkeypatch):
    import app.intelligence_assistant as ia
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Approved assistant evidence','original_content':'Source says Bawaslu requested clarification about an election supervision issue.',
      'jurisdiction_type':'National','confirm_jurisdiction':True,
      'ai_suggestions':{'_version':3,'summary':'Approved factual summary','signal_reason':'RAW UNAPPROVED SECRET CLAIM','screening_confidence':'HIGH','priority':'High','evidence_type':'OBSERVED','confidence':'HIGH'}
    }},headers=h)
    iid=r.json()['item']['id']
    r=client.post('/api/functions/intelligence',json={'action':'triageDecision','data':{'key':'summary','status':'Human Accepted'},'id':iid},headers=h)
    assert r.status_code==200, r.text
    captured={}
    def fake_provider(question,previous,records):
        captured['records']=records
        rid=records[0]['record_id']
        return {'answer_summary':'Grounded answer','key_observations':[f'[{rid}] Approved evidence used.'],'evidence_status':['Source status retained.'],'limitations':[],'cited_record_ids':[rid]}, {'mode':'OPENAI_GROUNDED','model':'gpt-test','usage':{'total_tokens':10}}
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setattr(ia,'generate_openai_assistant_answer',fake_provider)
    r=client.post('/api/functions/intelligenceAssistant',json={'question':'What does the approved evidence say?'},headers=h)
    assert r.status_code==200, r.text
    record=captured['records'][0]
    assert record['human_approved_triage']['summary']=='Approved factual summary'
    assert 'RAW UNAPPROVED SECRET CLAIM' not in json.dumps(record)
    assert r.json()['provider']['mode']=='OPENAI_GROUNDED'

def test_intelligence_assistant_filters_hallucinated_citations(monkeypatch):
    import app.intelligence_assistant as ia
    h=auth()
    r=client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Citation filter test','original_content':'Recorded Bawaslu evidence for citation testing.',
      'jurisdiction_type':'National','confirm_jurisdiction':True
    }},headers=h)
    real_id=r.json()['item']['intelligence_id']
    def fake_provider(question,previous,records):
        return {'answer_summary':'Test answer','key_observations':[f'[{real_id}] Supported.'],'evidence_status':[],'limitations':[],'cited_record_ids':[real_id,'INT-2099-999999']}, {'mode':'OPENAI_GROUNDED','model':'gpt-test','usage':{}}
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setattr(ia,'generate_openai_assistant_answer',fake_provider)
    r=client.post('/api/functions/intelligenceAssistant',json={'question':'Show citation test evidence'},headers=h)
    assert r.status_code==200, r.text
    ids=[x['intelligence_id'] for x in r.json()['records']]
    assert real_id in ids
    assert 'INT-2099-999999' not in ids

def test_intelligence_assistant_falls_back_safely_on_provider_error(monkeypatch):
    import app.intelligence_assistant as ia
    h=auth()
    client.post('/api/functions/intelligence',json={'action':'create','data':{
      'title':'Fallback assistant record','original_content':'Bawaslu source evidence remains available if the provider fails.',
      'jurisdiction_type':'National','confirm_jurisdiction':True
    }},headers=h)
    def fail_provider(question,previous,records):
        raise ia.AssistantProviderError('provider_timeout','timeout')
    monkeypatch.setenv('OPENAI_API_KEY','test-key')
    monkeypatch.setattr(ia,'generate_openai_assistant_answer',fail_provider)
    r=client.post('/api/functions/intelligenceAssistant',json={'question':'What evidence is available?'},headers=h)
    assert r.status_code==200, r.text
    body=r.json()
    assert body['provider']['mode']=='DETERMINISTIC_FALLBACK'
    assert body['provider']['fallback_code']=='provider_timeout'
    assert body['records']
