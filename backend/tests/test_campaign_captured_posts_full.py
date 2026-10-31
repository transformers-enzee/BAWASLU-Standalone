"""No post sampling or cross-campaign/regional leakage in the full captured feed."""
import os,json
os.environ['DATABASE_URL']='sqlite:///:memory:'
import pytest
from app.db import Base,engine,SessionLocal
from app.models import User,AccessGrant,SocialListeningRun,SocialListeningResult,CampaignEvidence
from app.access import default_permissions,profile
from app.auth import hash_password
from app.socialcrawl import social_listening_action as action

def setup_function():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)

def user(db,name,role='National Administrator',scope='Nationwide',province=''):
    u=User(email=name+'@captured-qa.test',full_name=name,password_hash=hash_password('test'))
    db.add(u);db.flush()
    db.add(AccessGrant(user_id=u.id,access_role=role,geographic_scope=scope,province=province,
                       permissions_json=json.dumps(default_permissions(role)),status='Active'))
    db.commit();return profile(db,u)

def campaign(db,p,name):
    return action(db,p,'createCampaign',{'name':name,'primary_keywords':['pemilu'],'platforms':['tiktok']})['campaign']['id']

def add(db,cid,count,province=''):
    run=SocialListeningRun(query_json=json.dumps({'province':province}) if province else '{}',credits_used=0)
    db.add(run);db.flush()
    for i in range(count):
        row=SocialListeningResult(run_id=run.id,platform='tiktok',content_type='Post',
            text_content=f'Original post {i}',published_at='2026-10-29',
            author_name=f'Author {i}',canonical_url=f'https://example.com/posts/{run.id}/{i}')
        db.add(row);db.flush()
        db.add(CampaignEvidence(campaign_id=int(cid),result_id=row.id))
    db.commit()

def feed(db,p,cid,page=1,size=100):
    return action(db,p,'campaignCapturedPosts',{'page':page,'page_size':size},cid)

def test_complete_225_post_feed_read_only():
    db=SessionLocal();p=user(db,'feedAdmin');cid=campaign(db,p,'One');add(db,cid,225)
    pages=[feed(db,p,cid,page) for page in (1,2,3)]
    assert [len(x['evidence']) for x in pages]==[100,100,25]
    assert [x['has_more'] for x in pages]==[True,True,False]
    assert all(x['total']==225 and x['paid_provider_called'] is False for x in pages)
    ids=[post['id'] for page in pages for post in page['evidence']]
    assert len(ids)==len(set(ids))==225
    assert len(action(db,p,'campaignEvidence',{},cid)['evidence'])==200
    db.close()

def test_campaign_isolation_and_invalid_page_size():
    db=SessionLocal();p=user(db,'isolationAdmin');a=campaign(db,p,'A');b=campaign(db,p,'B')
    add(db,a,3);add(db,b,2)
    assert feed(db,p,a)['total']==3 and feed(db,p,b)['total']==2
    with pytest.raises(ValueError,match='page size'):feed(db,p,a,1,201)
    with pytest.raises(ValueError,match='Campaign not available'):feed(db,p,99999)
    db.close()

def test_regional_scope_excludes_nationwide_sources():
    db=SessionLocal();admin=user(db,'scopeAdmin');bali=user(db,'scopeBali','Provincial Analyst','Province','Bali')
    cid=campaign(db,bali,'Bali monitoring')
    add(db,cid,2,'Bali');add(db,cid,2)
    assert feed(db,bali,cid)['total']==2
    assert feed(db,admin,cid)['total']==4
    db.close()

def test_watchlist_account_posts_never_enter_social_listening_captured_posts():
    db=SessionLocal();p=user(db,'separateSources');cid=campaign(db,p,'Test')
    add(db,cid,3)
    run=SocialListeningRun(query_json='{}',credits_used=0)
    db.add(run);db.flush()
    for i in range(12):
        row=SocialListeningResult(run_id=run.id,platform='instagram',
            author_name='Gibran Rakabuming',observed_handle='@gibran_rakabuming',
            text_content='Original candidate-authored content',
            canonical_url=f'https://instagram.com/p/owned{i}',published_at='2026-10-30')
        db.add(row);db.flush()
        db.add(CampaignEvidence(campaign_id=int(cid),result_id=row.id,
            match_method='WATCHLIST_ACCOUNT'))
    db.commit()
    captured=feed(db,p,cid)
    assert captured['total']==len(captured['evidence'])==3
    assert all(x['platform']=='tiktok' for x in captured['evidence'])
    evidence=action(db,p,'campaignEvidence',{},cid)
    assert evidence['total']==len(evidence['evidence'])==3
    own_id=db.query(SocialListeningResult.id).filter(
        SocialListeningResult.platform=='instagram').first()[0]
    assert action(db,p,'campaignEvidenceById',{'result_id':str(own_id)},cid)['found'] is False
    assert db.query(CampaignEvidence).filter_by(campaign_id=int(cid)).count()==15
    db.close()

def test_account_collection_does_not_inflate_dashboard_queues_or_command_centre():
    from app.models import EvidenceAssessment
    from app.command_center import build_command_center
    db=SessionLocal();p=user(db,'sourceSeparation');cid=campaign(db,p,'Audit campaign')
    add(db,cid,3)
    run=SocialListeningRun(query_json='{}',credits_used=0)
    db.add(run);db.flush()
    for i in range(12):
        own=SocialListeningResult(run_id=run.id,platform='instagram',
            author_name='Gibran Rakabuming',observed_handle='@gibran_rakabuming',
            text_content='Registered candidate profile post',
            canonical_url=f'https://www.instagram.com/p/account{i}/',
            published_at='2026-10-29T01:00:00Z',engagement_json='{}')
        db.add(own);db.flush()
        db.add(CampaignEvidence(campaign_id=int(cid),result_id=own.id,
            match_method='WATCHLIST_ACCOUNT'))
        # Even accidentally assessed Watchlist-only rows MUST NOT contaminate
        # generic captured-post analytics or Command Centre electoral alerts.
        db.add(EvidenceAssessment(campaign_id=int(cid),result_id=own.id,
            assessment_version=1,relevance_label='RELEVANT',
            sentiment='NEGATIVE',candidate_signals_json='["Gibran"]'))
    db.commit()
    assert action(db,p,'campaignDashboard',{},cid)['evidence_count']==3
    assert action(db,p,'campaignDashboard',{},cid)['sentiment']['Unclassified']==3
    assert action(db,p,'campaignSentimentBatchPreview',{},cid)['eligible_total']==3
    assert action(db,p,'campaignAssessmentBacklogPreview',
        {'sample_limit':20},cid)['unassessed']==3
    from app.prism_discover import action as prism_action
    assert prism_action(db,p,'campaignCandidateSuggestions',{},cid)['candidates']==[]
    cc=build_command_center(db,p,{'period':'all'})
    assert cc['activity']['captured_mentions']==3
    assert cc['indicators']['relevant_mentions']==0
    assert cc['paid_provider_called'] is False
    db.close()
