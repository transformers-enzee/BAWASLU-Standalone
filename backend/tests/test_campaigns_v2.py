"""Architecture v2 Campaigns: permission, data integrity, lifecycle and cost gates."""
import json
import os
os.environ['DATABASE_URL']='sqlite:///:memory:'
import pytest
from app.db import Base, engine, SessionLocal
from app.models import (User, AccessGrant, MonitoringCampaign, CampaignRun,
                        SocialListeningRun, SocialListeningResult, CampaignEvidence)
from app.auth import hash_password
from app.access import default_permissions, profile
from app.socialcrawl import social_listening_action

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def actor(db, name, role, scope='Nationwide', province='',city=''):
    user=User(email=name+'@campaign-qa.local',full_name=name,password_hash=hash_password('test'))
    db.add(user);db.flush()
    db.add(AccessGrant(user_id=user.id,access_role=role,geographic_scope=scope,
       province=province,regency_city=city,
       permissions_json=json.dumps(default_permissions(role)),status='Active'))
    db.commit()
    return profile(db,user)

def payload(**kwargs):
    result={'name':'Election 2029','description':'Monitoring candidate narratives',
            'primary_keywords':['Gibran','GIBRAN','pemilu'],
            'secondary_keywords':['Wapres'],'excluded_keywords':['music'],
            'platforms':['tiktok','youtube'],'language':'id',
            'interval_minutes':180,'date_from':'2026-10-01','date_to':'2026-10-22'}
    result.update(kwargs)
    return result

def action(db,p,verb,data=None,id=None):
    return social_listening_action(db,p,verb,data or {},id)

def test_create_is_draft_and_does_not_spend_credits_or_make_crawl_runs():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    result=action(db,p,'createCampaign',payload())
    c=result['campaign']
    assert c['status']=='DRAFT'
    assert c['primary_keywords']==['Gibran','pemilu']
    assert c['platforms']==['tiktok','youtube']
    assert c['interval_minutes']==180 and c['next_run_at'] is None
    assert db.query(MonitoringCampaign).count()==1
    assert db.query(SocialListeningRun).count()==0
    assert db.query(CampaignRun).count()==0
    assert db.query(SocialListeningResult).count()==0
    assert db.query(CampaignEvidence).count()==0
    assert action(db,p,'getCampaign',{},c['id'])['campaign']['name']=='Election 2029'
    lst=action(db,p,'listCampaigns')
    assert lst['total']==1
    assert lst['automatic_paid_crawling_enabled'] is False
    db.close()

def test_update_and_pause_are_persistent_and_activation_is_blocked():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=action(db,p,'createCampaign',payload())['campaign']
    updated=action(db,p,'updateCampaign',{'secondary_keywords':['campaign'],'status':'PAUSED'},c['id'])['campaign']
    assert updated['status']=='PAUSED' and updated['secondary_keywords']==['campaign']
    assert action(db,p,'getCampaign',{},c['id'])['campaign']['status']=='PAUSED'
    with pytest.raises(ValueError,match='activation'):
        action(db,p,'updateCampaign',{'status':'ACTIVE'},c['id'])
    db.refresh(db.get(MonitoringCampaign,int(c['id'])))
    assert db.get(MonitoringCampaign,int(c['id'])).status=='PAUSED'
    assert db.query(CampaignRun).count()==0
    db.close()

@pytest.mark.parametrize('change',[
    {'name':''}, {'primary_keywords':[]},
    {'primary_keywords':['money'],'excluded_keywords':['MONEY']},
    {'platforms':[]}, {'platforms':['invalid']},
    {'interval_minutes':59}, {'interval_minutes':True},
    {'date_from':'2026-10-24','date_to':'2026-10-01'},
    {'date_from':'not-a-date'}, {'language':'xx'},
    {'secondary_keywords':'one,two'}, {'primary_keywords':['k']*31}
])
def test_invalid_campaign_payloads_rejected(change):
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    with pytest.raises(ValueError):
        action(db,p,'createCampaign',payload(**change))
    assert db.query(MonitoringCampaign).count()==0
    db.close()

def test_provincial_campaign_scope_and_visibility():
    db=SessionLocal()
    bali=actor(db,'bali','Provincial Analyst','Province','Bali')
    java=actor(db,'java','Provincial Analyst','Province','Jawa Barat')
    national=actor(db,'national','National Administrator')
    created=action(db,bali,'createCampaign',payload())['campaign']
    assert created['province']=='Bali'
    assert action(db,bali,'listCampaigns')['total']==1
    assert action(db,java,'listCampaigns')['total']==0
    assert action(db,national,'listCampaigns')['total']==1
    with pytest.raises(ValueError,match='not available'):
        action(db,java,'getCampaign',{},created['id'])
    with pytest.raises(PermissionError):
        action(db,bali,'createCampaign',payload(province='Jawa Barat'))
    # Conceal the existence of out-of-scope records, rather than revealing authorization details.
    with pytest.raises(ValueError,match='not available'):
        action(db,java,'updateCampaign',{'name':'attack'},created['id'])
    db.close()

def test_owner_or_administrator_can_edit_but_other_analyst_cannot():
    db=SessionLocal()
    one=actor(db,'one','Provincial Analyst','Province','Bali')
    two=actor(db,'two','Provincial Analyst','Province','Bali')
    admin=actor(db,'admin','National Administrator')
    campaign=action(db,one,'createCampaign',payload())['campaign']
    with pytest.raises(PermissionError,match='owner'):
        action(db,two,'updateCampaign',{'name':'Changed'},campaign['id'])
    result=action(db,admin,'updateCampaign',{'name':'Reviewed campaign'},campaign['id'])
    assert result['campaign']['name']=='Reviewed campaign'
    db.close()

def test_viewer_cannot_create_campaign():
    db=SessionLocal();p=actor(db,'viewer','National Leadership')
    with pytest.raises(PermissionError):
        action(db,p,'createCampaign',payload())
    assert action(db,p,'listCampaigns')['total']==0
    db.close()


def test_campaign_credit_preview_is_read_only_and_scoped():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    result=action(db,p,'campaignCostPreview',payload(platforms=['tiktok','linkedin','online_news']))
    assert result['estimated_credits']==14  # 2 keywords * (TikTok 1 + LinkedIn 5 + news 1)
    all_sources=action(db,p,'campaignCostPreview',payload(platforms=['search_everywhere']))
    assert all_sources['estimated_credits']==20
    assert all_sources['paid_run_enabled'] is False
    assert all_sources['retrieval_mode']=='SEARCH_EVERYWHERE_PREVIEW'
    assert result['paid_run_enabled'] is False
    assert result['approval_required'] is True
    assert db.query(MonitoringCampaign).count()==0
    assert db.query(SocialListeningRun).count()==0
    assert db.query(SocialListeningResult).count()==0
    regional=actor(db,'regional','Provincial Analyst','Province','Bali')
    with pytest.raises(PermissionError):
        action(db,regional,'campaignCostPreview',payload(province='Jawa Barat'))
    db.close()

def test_campaign_keyword_preview_is_no_charge_and_scope_enforced():
    db=SessionLocal();owner=actor(db,'admin','National Administrator')
    campaign=action(db,owner,'createCampaign',payload(primary_keywords=['bawaslu','pemilu'],secondary_keywords=['Gibran'],excluded_keywords=['concert']))['campaign']
    one=action(db,owner,'campaignKeywordPreview',{'text':'Pemilu election news'},campaign['id'])
    assert one['screening']['matched'] is True
    assert one['screening']['main_keywords']==['pemilu']
    assert one['screening']['secondary_keywords']==[]
    two=action(db,owner,'campaignKeywordPreview',{'text':'Bawaslu Gibran concert'},campaign['id'])
    assert two['screening']['matched'] is False
    assert two['screening']['excluded_keywords']==['concert']
    assert one['paid_provider_called'] is False
    assert db.query(SocialListeningRun).count()==0
    assert db.query(CampaignRun).count()==0
    db.close()

def test_campaign_evidence_read_only_no_charge():
    db=SessionLocal();p=actor(db,'admin','National Administrator')
    c=action(db,p,'createCampaign',payload())['campaign']
    result=action(db,p,'campaignEvidence',{},c['id'])
    assert result['evidence']==[] and result['paid_provider_called'] is False
    assert db.query(SocialListeningRun).count()==0
    db.close()


def test_campaign_dashboard_word_cloud_without_secondary_keywords():
    db=SessionLocal(); p=actor(db,'wordcloudadmin','National Administrator')
    campaign=action(db,p,'createCampaign',payload(primary_keywords=['bawaslu','pemilu'],secondary_keywords=[]))['campaign']
    result=action(db,p,'campaignDashboard',{},campaign['id'])
    assert result['word_cloud']==[]
    assert result['secondary_word_counts']=={}
    assert result['paid_provider_called'] is False
    db.close()


def test_demographics_coverage_is_zero_when_provider_metadata_missing():
    db=SessionLocal(); p=actor(db,'demographicqa','National Administrator')
    campaign=action(db,p,'createCampaign',payload(primary_keywords=['bawaslu'],secondary_keywords=[]))['campaign']
    dashboard=action(db,p,'campaignDashboard',{},campaign['id'])
    assert dashboard['demographics_coverage']=={'records':0,'language_available':0,'country_available':0,'age_available':0,'gender_available':0}
    assert dashboard['source_languages']=={}
    db.close()


def test_thumbnail_recovery_no_existing_evidence_does_not_call_provider():
    db=SessionLocal(); p=actor(db,'thumbnailrecover','National Administrator')
    campaign=action(db,p,'createCampaign',payload())['campaign']
    result=action(db,p,'campaignThumbnailRecovery',{},campaign['id'])
    assert result['checked']==0 and result['recovered']==0
    assert result['paid_provider_called'] is False
    db.close()

def test_search_everywhere_campaign_preview_is_safe_for_schedule_and_manual():
    db=SessionLocal();p=actor(db,'everywhere_admin','National Administrator')
    campaign=action(db,p,'createCampaign',payload(platforms=['search_everywhere']))['campaign']
    cost=action(db,p,'campaignCostPreview',payload(platforms=['search_everywhere']))
    assert cost['estimated_credits']==20
    preview=action(db,p,'campaignManualPreflight',{},campaign['id'])
    assert preview['estimated_credits']==20 and preview['can_run'] is False
    schedule=action(db,p,'campaignSchedulePreview',{},campaign['id'])
    assert schedule['schedule']['estimated_credits_per_run']==20
    with pytest.raises(ValueError,match='explicit Search Everywhere query'):
        action(db,p,'campaignManualRun',{'confirm_cost':True,'confirmed_credits':20},campaign['id'])
    approved=action(db,p,'campaignManualPreflight',{'everywhere_query':'bawaslu pemilu'},campaign['id'])
    assert approved['estimated_credits']==20 and approved['can_run'] is True
    with pytest.raises(ValueError,match='Explicit credit confirmation'):
        action(db,p,'campaignManualRun',{'everywhere_query':'bawaslu pemilu'},campaign['id'])
    with pytest.raises(ValueError,match='Search query changed'):
        action(db,p,'campaignManualRun',{'everywhere_query':'bawaslu pemilu','confirmed_query':'different','confirm_cost':True,'confirmed_credits':20},campaign['id'])
    assert db.query(SocialListeningRun).count()==0
    db.close()

def test_search_everywhere_does_not_send_internal_platform_as_provider_source():
    from app.socialcrawl import _provider_params
    params=_provider_params({'query':'iphone','platforms':['search_everywhere']})
    assert params['query']=='iphone'
    assert 'sources' not in params
    assert 'search_everywhere' not in str(params)
