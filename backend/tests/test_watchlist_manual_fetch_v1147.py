"""No-cost profile collection tests: manual consent, campaign evidence, authorship."""
import json
import os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app.db import Base,engine,SessionLocal
from app.auth import hash_password
from app.access import profile,default_permissions
from app.registry import registry_action
from app.watchlist_auto import sync_account
from app.models import (User,AccessGrant,WatchlistItem,SourceAccount,
    MonitoringCampaign,SocialListeningRun,SocialListeningResult,
    WatchlistAccountEvidence,CampaignEvidence,WatchlistAccountSync)

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def setup(db):
    user=User(email='watchlist-manual@qa.local',full_name='Manual Watchlist QA',
        password_hash=hash_password('test'))
    db.add(user);db.flush()
    db.add(AccessGrant(user_id=user.id,access_role='National Administrator',
        geographic_scope='Nationwide',permissions_json=json.dumps(
        default_permissions('National Administrator')),status='Active'))
    watch=WatchlistItem(name='Gibran Rakabuming Raka',type='Candidate',status='Active')
    campaign=MonitoringCampaign(name='Gibran QA Campaign',created_by=str(user.id))
    db.add_all([watch,campaign]);db.flush()
    account=SourceAccount(watchlist_id=watch.id,platform='instagram',
        url='https://www.instagram.com/gibran_rakabuming',
        handle='@gibran_rakabuming')
    db.add(account);db.commit()
    db.add(WatchlistAccountSync(account_id=account.id,state='PENDING'))
    db.commit()
    return profile(db,user),watch,campaign,account

def envelope(author='gibran_rakabuming'):
    return {'success':True,'data':{'results':[{
        'status':'ok',
        'data':{'author':{'username':'gibran_rakabuming'}},
        'posts':{'status':'ok','items':[{'post':{
            'id':'instagram-501',
            'url':'https://www.instagram.com/p/qa01/',
            'author':{'username':author,'display_name':'Publisher'},
            'content':{'text':'A public source post'},
            'published_at':'2026-10-30T00:00:00Z'
        }}]}
    }]},'credits_used':2,'credits_remaining':80,'request_id':'mock-request'}

def test_manual_fetch_blocks_when_budget_unconfigured(monkeypatch):
    monkeypatch.setenv('SOCIALCRAWL_API_KEY','offline-test-only')
    monkeypatch.delenv('BAWASLU_WATCHLIST_DAILY_CREDIT_BUDGET',raising=False)
    db=SessionLocal();actor,watch,campaign,account=setup(db)
    result=registry_action(db,actor,'requestAccountFetch',{
        'account_id':str(account.id),'campaign_id':str(campaign.id)},str(watch.id))
    assert result['status']=='BLOCKED'
    assert result['paid_provider_called'] is False
    assert db.query(SocialListeningRun).count()==0
    db.close()

def test_manual_first_fetch_saves_own_post_in_campaign(monkeypatch):
    monkeypatch.setenv('SOCIALCRAWL_API_KEY','offline-test-only')
    monkeypatch.setenv('BAWASLU_WATCHLIST_DAILY_CREDIT_BUDGET','2')
    monkeypatch.setenv('BAWASLU_WATCHLIST_AUTO_FETCH_ENABLED','false')
    db=SessionLocal();actor,watch,campaign,account=setup(db)
    requested=registry_action(db,actor,'requestAccountFetch',{
        'account_id':str(account.id),'campaign_id':str(campaign.id)},str(watch.id))
    assert requested['status']=='QUEUED'
    calls=[]
    result=sync_account(account.id,
        client=lambda payload:(calls.append(payload) or envelope()),
        campaign_id=campaign.id,manual=True)
    assert result['status']=='COMPLETED',result
    assert len(calls)==1 and calls[0]['include']=='posts'
    assert len(db.query(SocialListeningResult).all())==1
    assert db.query(CampaignEvidence).count()==1
    assert db.query(WatchlistAccountEvidence).count()==1
    feed=registry_action(db,actor,'watchlistCapturedFeed',{
        'campaign_id':str(campaign.id)},str(watch.id))
    assert feed['own_posts']==1 and feed['mentions_by_others']==0
    assert feed['posts'][0]['author_name']=='Publisher'
    assert feed['posts'][0]['relation']=='OWN_POST'
    db.close()

def test_mismatched_author_never_saved_as_candidate_post(monkeypatch):
    monkeypatch.setenv('SOCIALCRAWL_API_KEY','offline-test-only')
    monkeypatch.setenv('BAWASLU_WATCHLIST_DAILY_CREDIT_BUDGET','2')
    monkeypatch.setenv('BAWASLU_WATCHLIST_AUTO_FETCH_ENABLED','false')
    db=SessionLocal();actor,watch,campaign,account=setup(db)
    result=sync_account(account.id,client=lambda _:envelope('ntvnews.id'),
        campaign_id=campaign.id,manual=True)
    assert result['status']=='COMPLETED',result
    assert db.query(WatchlistAccountEvidence).count()==0
    assert db.query(CampaignEvidence).count()==0
    assert db.query(SocialListeningResult).count()==0
    db.close()

def test_account_id_is_scoped_to_candidate(monkeypatch):
    monkeypatch.setenv('SOCIALCRAWL_API_KEY','offline-test-only')
    monkeypatch.setenv('BAWASLU_WATCHLIST_DAILY_CREDIT_BUDGET','2')
    db=SessionLocal();actor,watch,campaign,account=setup(db)
    other=WatchlistItem(name='Another candidate',type='Candidate',status='Active')
    db.add(other);db.commit()
    try:
        registry_action(db,actor,'requestAccountFetch',{
            'account_id':str(account.id),'campaign_id':str(campaign.id)},str(other.id))
    except ValueError as e:
        assert 'does not belong' in str(e)
    else:assert False,'Cross-candidate account fetch must be denied'
    db.close()
