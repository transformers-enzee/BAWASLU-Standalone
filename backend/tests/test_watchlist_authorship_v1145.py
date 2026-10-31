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

def test_campaign_mentions_are_only_saved_captured_posts_not_account_or_global_feeds():
    db,p,w,c,r=make_db()
    account=SourceAccount(watchlist_id=w.id,platform='instagram',
        handle='@gibran_rakabuming',
        url='https://www.instagram.com/gibran_rakabuming')
    db.add(account);db.flush()
    # A third-party article from the selected campaign's captured posts.
    mention=add_post(db,r,c,author='ntvnews.id',handle='ntvnews.id',
        text='Gibran menjadi topik berita pemilu')
    # Not about the candidate, even though it belongs to this campaign.
    unrelated=add_post(db,r,c,author='othernews.id',handle='othernews.id',
        text='Berita umum mengenai pengawasan dan penghitungan suara')
    # Another campaign's capture must never appear in the Test campaign.
    other=MonitoringCampaign(name='Unrelated monitoring campaign',
        created_by=str(p['id']),status='DRAFT')
    db.add(other);db.commit()
    external=add_post(db,r,other,author='outside.id',handle='outside.id',
        text='Gibran dibahas oleh media dari campaign lain')
    # Candidate's actual Instagram-author posts are the separate Own Posts.
    own=SocialListeningResult(run_id=r.id,platform='instagram',
        provider_result_id='candidate-own-01',
        author_name='Gibran Rakabuming',observed_handle='@gibran_rakabuming',
        canonical_url='https://www.instagram.com/p/qa-original/',
        text_content='Posting langsung dari akun resmi',published_at='2026-10-30T13:10:55Z')
    db.add(own);db.flush()
    db.add(CampaignEvidence(campaign_id=c.id,result_id=own.id,
        match_method='WATCHLIST_ACCOUNT'))
    db.add(WatchlistAccountEvidence(account_id=account.id,result_id=own.id))
    # A wrongly linked non-candidate author, even if their text says Gibran,
    # cannot become an extra Mentions by Others row from account collection.
    wrong=SocialListeningResult(run_id=r.id,platform='instagram',
        provider_result_id='not-an-own-post-01',author_name='news_reporter',
        observed_handle='@news_reporter',
        canonical_url='https://www.instagram.com/p/qa-third-party/',
        text_content='Berita tentang Gibran',published_at='2026-10-30T13:10:55Z')
    db.add(wrong);db.flush()
    db.add(CampaignEvidence(campaign_id=c.id,result_id=wrong.id,
        match_method='WATCHLIST_ACCOUNT'))
    db.add(WatchlistAccountEvidence(account_id=account.id,result_id=wrong.id))
    db.commit()
    result=feed(db,p,c,w)
    assert result['total']==2
    assert result['own_posts']==1
    assert result['mentions_by_others']==1
    rows={x['id']:x for x in result['posts']}
    assert set(rows)=={str(mention.id),str(own.id)}
    assert rows[str(mention.id)]['relation']=='THIRD_PARTY_MENTION'
    assert rows[str(mention.id)]['source_collection']=='SOCIAL_LISTENING_CAPTURED'
    assert rows[str(mention.id)]['campaign_id']==str(c.id)
    assert rows[str(own.id)]['relation']=='OWN_POST'
    assert rows[str(own.id)]['source_collection']=='REGISTERED_CANDIDATE_ACCOUNT'
    assert all(x not in rows for x in (str(unrelated.id),str(external.id),str(wrong.id)))
    db.close()


def test_all_captured_gibran_mentions_are_paginated_without_new_crawls():
    from app.models import SocialListeningProviderUsage
    db,p,w,c,r=make_db()
    db.add(SourceAccount(watchlist_id=w.id,platform='instagram',
        handle='@gibran_rakabuming',url='https://www.instagram.com/gibran_rakabuming'))
    db.commit()
    for i in range(58):
        row=add_post(db,r,c,author='news_'+str(i),handle='news_'+str(i),
            text='Perbincangan publik tentang Gibran di media sosial')
    posts=[]
    for page in (1,2):
        chunk=registry_action(db,p,'watchlistCapturedFeed',
            {'campaign_id':str(c.id),'page':page,'page_size':50},str(w.id))
        assert chunk['total']==58
        assert chunk['own_posts']==0
        assert chunk['mentions_by_others']==58
        posts.extend(chunk['posts'])
    assert len(posts)==58
    assert len({x['id'] for x in posts})==58
    assert all(x['source_collection']=='SOCIAL_LISTENING_CAPTURED' for x in posts)
    assert db.query(SocialListeningProviderUsage).count()==0
    db.close()
