"""Offline regression: a candidate name in a news post is NOT authorship."""
import json,os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app.db import Base,engine,SessionLocal
from app.auth import hash_password
from app.access import default_permissions,profile
from app.registry import registry_action
from app.models import (User,AccessGrant,WatchlistItem,MonitoringCampaign,
    SocialListeningRun,SocialListeningResult,CampaignEvidence,SourceAccount,
    WatchlistAccountEvidence)

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def make_db():
    db=SessionLocal()
    user=User(email='authorship@qa.local',full_name='Authorship QA',
        password_hash=hash_password('example'))
    db.add(user);db.flush()
    db.add(AccessGrant(user_id=user.id,access_role='National Administrator',
        geographic_scope='Nationwide',permissions_json=json.dumps(
        default_permissions('National Administrator')),status='Active'))
    candidate=WatchlistItem(name='Gibran Rakabuming Raka',type='Candidate',
        status='Active')
    campaign=MonitoringCampaign(name='Gibran test campaign',created_by=str(user.id),
        status='DRAFT')
    run=SocialListeningRun(provider='SOCIALCRAWL_PRISM',status='COMPLETED')
    db.add_all([candidate,campaign,run]);db.commit()
    return db,profile(db,user),candidate,campaign,run

def add_post(db,run,campaign,author='ntvnews.id',handle='ntvnews.id',
             text='Berita tentang Gibran Rakabuming Raka'):
    row=SocialListeningResult(run_id=run.id,platform='tiktok',
        provider_result_id='test-'+str(db.query(SocialListeningResult).count()),
        canonical_url='https://www.tiktok.com/@'+handle+'/video/1234',
        author_name=author,observed_handle=handle,text_content=text,
        published_at='2026-10-30T13:10:55Z')
    db.add(row);db.flush()
    db.add(CampaignEvidence(campaign_id=campaign.id,result_id=row.id))
    db.commit()
    return row

def feed(db,p,campaign,watch):
    return registry_action(db,p,'watchlistCapturedFeed',
        {'campaign_id':str(campaign.id),'page':1,'page_size':50},str(watch.id))

def test_news_article_is_mention_when_no_accounts_registered():
    db,p,w,c,r=make_db()
    row=add_post(db,r,c)
    result=feed(db,p,c,w)
    assert result['total']==1
    assert result['own_posts']==0
    assert result['mentions_by_others']==1
    assert result['posts'][0]['relation']=='THIRD_PARTY_MENTION'
    assert result['posts'][0]['author_name']=='ntvnews.id'
    db.close()

def test_account_evidence_link_cannot_override_mismatched_author():
    db,p,w,c,r=make_db()
    row=add_post(db,r,c)
    account=SourceAccount(watchlist_id=w.id,platform='tiktok',handle='@officialgibran',
        url='https://www.tiktok.com/@officialgibran')
    db.add(account);db.flush()
    db.add(WatchlistAccountEvidence(account_id=account.id,result_id=row.id))
    db.commit()
    result=feed(db,p,c,w)
    assert result['total']==1
    assert result['own_posts']==0
    assert result['mentions_by_others']==1
    assert result['posts'][0]['relation']=='THIRD_PARTY_MENTION'
    assert result['posts'][0]['author_name']=='ntvnews.id'
    assert result['posts'][0]['account']==''
    db.close()

def test_registered_matching_author_is_own_post():
    db,p,w,c,r=make_db()
    account=SourceAccount(watchlist_id=w.id,platform='tiktok',handle='@officialgibran',
        url='https://www.tiktok.com/@officialgibran')
    db.add(account);db.commit()
    row=add_post(db,r,c,author='officialgibran',handle='@officialgibran',
        text='Post by the account, no candidate name in text')
    result=feed(db,p,c,w)
    assert result['total']==1
    assert result['own_posts']==1
    assert result['mentions_by_others']==0
    assert result['posts'][0]['relation']=='OWN_POST'
    db.close()

def test_16_saved_mentions_remain_visible_after_instagram_registration():
    """Candidate account registration must not erase campaign mentions."""
    db,p,w,c,r=make_db()
    db.add(SourceAccount(watchlist_id=w.id,platform='instagram',
        handle='@gibran_rakabuming',
        url='https://www.instagram.com/gibran_rakabuming'))
    db.commit()
    for index in range(16):
        author='ntvnews.id' if index==0 else 'reporter_'+str(index)
        # Typical provider results use the short candidate name, not the
        # full registered Watchlist name.
        add_post(db,r,c,author=author,handle=author,
            text='Berita tentang Gibran dan pemilihan.')
    result=feed(db,p,c,w)
    assert result['total']==16
    assert result['own_posts']==0
    assert result['mentions_by_others']==16
    assert len(result['posts'])==16
    assert all(post['relation']=='THIRD_PARTY_MENTION'
               for post in result['posts'])
    assert any(post['author_name']=='ntvnews.id'
               for post in result['posts'])
    db.close()
