"""Budget-capped public-account post collection for Watchlist.

Opt-in only: disabled unless an administrator configures both the feature flag
and a positive 24-hour credit budget. Each run requests only the first feed
page. No live claim of instantaneous delivery is made.
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
import httpx
from sqlalchemy import func, or_, text
from .db import SessionLocal
from .models import (SourceAccount, WatchlistItem, WatchlistAccountSync,
                     WatchlistAccountEvidence, SocialListeningResult,
                     SocialListeningRun, SocialListeningProviderUsage)

LOG=logging.getLogger(__name__)
PROVIDER_BASE='https://www.socialcrawl.dev'
SUPPORTED={'instagram','tiktok','youtube','facebook','x','threads','reddit'}
# LinkedIn profiles are 5 credits before post pages. Deliberately excluded
# from the two-credit first-page collector.
RESERVED_CREDITS=2

def _integer_env(name,default=0):
    try:return max(0,int(os.getenv(name,str(default))))
    except (ValueError,TypeError):return 0

def auto_enabled():
    return os.getenv('BAWASLU_WATCHLIST_AUTO_FETCH_ENABLED','false').lower()=='true'

def daily_budget():
    return _integer_env('BAWASLU_WATCHLIST_DAILY_CREDIT_BUDGET')

def interval_minutes():
    return max(15,min(1440,_integer_env('BAWASLU_WATCHLIST_SYNC_INTERVAL_MINUTES',60)))

def readiness():
    return {'enabled':auto_enabled() and daily_budget()>=RESERVED_CREDITS and bool(os.getenv('SOCIALCRAWL_API_KEY')),
            'feature_enabled':auto_enabled(),
            'manual_fetch_available':daily_budget()>=RESERVED_CREDITS and bool(os.getenv('SOCIALCRAWL_API_KEY')),
            'daily_credit_limit':daily_budget(),'estimated_max_credits_per_check':RESERVED_CREDITS,
            'interval_minutes':interval_minutes(),
            'provider_configured':bool(os.getenv('SOCIALCRAWL_API_KEY')),
            'note':'New posts are checked periodically while the worker is running. This is not real-time push delivery.'}

def identity(account):
    platform=str(account.platform or '').strip().casefold()
    if platform in ('twitter','twitter-ai-search'):platform='x'
    if platform not in SUPPORTED:return platform,''
    handle=str(account.handle or '').strip().lstrip('@')
    if not handle:
        parsed=urlparse(account.url or '')
        host=(parsed.hostname or '').lower()
        path=(parsed.path or '').strip('/').split('/')
        if platform=='youtube':
            if path and path[0].startswith('@'):handle=path[0].lstrip('@')
        elif platform in ('instagram','tiktok','x','threads','facebook'):
            handle=path[0].lstrip('@') if path and path[0].lower() not in ('p','reel','reels','video','watch','status','posts','groups','profile.php') else ''
        elif platform=='reddit':
            handle=path[1] if len(path)>1 and path[0].lower() in ('user','u') else ''
    return platform,handle.casefold()

def ensure_rows(db):
    for account in db.query(SourceAccount).all():
        if db.get(WatchlistAccountSync,account.id) is None:
            db.add(WatchlistAccountSync(account_id=account.id,state='PENDING',
                                         next_check_at=datetime.utcnow()))
    db.commit()

def status_for(db,watchlist_id):
    accounts=db.query(SourceAccount).filter(SourceAccount.watchlist_id==watchlist_id).all()
    rows={a.account_id:a for a in db.query(WatchlistAccountSync).filter(
        WatchlistAccountSync.account_id.in_([x.id for x in accounts])).all()} if accounts else {}
    return {**readiness(),'accounts':[{
        'account_id':str(a.id),'platform':a.platform,'handle':a.handle,
        'state':rows[a.id].state if a.id in rows else 'PENDING',
        'last_checked_at':rows[a.id].last_checked_at.isoformat() if a.id in rows and rows[a.id].last_checked_at else None,
        'next_check_at':rows[a.id].next_check_at.isoformat() if a.id in rows and rows[a.id].next_check_at else None,
        'last_error':rows[a.id].last_error if a.id in rows else '',
        'last_new_posts':rows[a.id].last_new_posts if a.id in rows else 0,
        'total_posts':rows[a.id].total_posts if a.id in rows else 0
    } for a in accounts]}

def mark_pending(db,account_id):
    row=db.get(WatchlistAccountSync,account_id)
    if not row:
        row=WatchlistAccountSync(account_id=account_id)
        db.add(row)
    row.state='PENDING'
    row.next_check_at=datetime.utcnow()
    row.last_error=''
    db.commit()

def _claim(db,account_id,manual=False):
    now=datetime.utcnow()
    ready=readiness()
    if not (ready['manual_fetch_available'] if manual else ready['enabled']):return False
    if db.bind.dialect.name=='postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(8700875)'))
    row=db.query(WatchlistAccountSync).filter(
        WatchlistAccountSync.account_id==account_id).with_for_update().first()
    account=db.get(SourceAccount,account_id)
    watch=db.get(WatchlistItem,account.watchlist_id) if account else None
    if not row or not account or not watch or watch.status!='Active':db.rollback();return False
    if row.state=='RUNNING' and row.started_at and row.started_at>now-timedelta(minutes=10):
        db.rollback();return False
    if row.state in ('UNSUPPORTED','NEEDS_HANDLE'):
        db.rollback();return False
    if row.next_check_at and row.next_check_at>now and not manual:
        db.rollback();return False
    if manual and row.last_checked_at and row.last_checked_at>now-timedelta(minutes=15):
        db.rollback();return False
    platform,handle=identity(account)
    if platform not in SUPPORTED or not handle:
        row.state='NEEDS_HANDLE' if platform in SUPPORTED else 'UNSUPPORTED'
        row.last_error='Enter a supported public account handle or profile URL.'
        db.commit();return False
    used=db.query(func.sum(SocialListeningProviderUsage.credits_used)).filter(
        SocialListeningProviderUsage.created_at>=now-timedelta(hours=24)).scalar() or 0
    reserved=db.query(func.count(WatchlistAccountSync.account_id)).filter(
        WatchlistAccountSync.state=='RUNNING',
        WatchlistAccountSync.started_at>=now-timedelta(minutes=10)).scalar() or 0
    if int(used)+int(reserved)*RESERVED_CREDITS+RESERVED_CREDITS>daily_budget():
        row.state='BUDGET_PAUSED'
        row.next_check_at=now+timedelta(hours=1)
        row.last_error='24-hour SocialCrawl budget reached. Automatic collection paused.'
        db.commit();return False
    row.state='RUNNING';row.started_at=now;row.last_error=''
    db.commit();return True

def sync_account(account_id,client=None,campaign_id=None,manual=False):
    """Run one idempotent, capped first-page sync; injected client permits offline tests."""
    db=SessionLocal()
    try:
        if not _claim(db,account_id,manual=manual):return {'status':'SKIPPED'}
        account=db.get(SourceAccount,account_id)
        watch=db.get(WatchlistItem,account.watchlist_id)
        platform,handle=identity(account)
        now=datetime.utcnow()
        query={'watchlist_id':watch.id,'account_id':account.id,'platform':platform,
               'handle':handle,'province':'','regency_city':''}
        run=SocialListeningRun(query_json=json.dumps(query),executed_by='watchlist-auto',
                               status='RUNNING')
        db.add(run);db.commit();db.refresh(run)
        credits=0
        try:
            api_key=os.getenv('SOCIALCRAWL_API_KEY','')
            if not api_key and client is None:raise RuntimeError('SocialCrawl API key is not configured')
            last_known=(db.get(WatchlistAccountSync,account_id).last_post_id or '').strip()
            item_request={'platform':platform,'handle':handle}
            if last_known:item_request['stop_at_id']=last_known
            payload={'include':'posts','items':[item_request]}
            # Idempotency for the same reserved worker attempt; retries never
            # repeat a billable request within the provider's 24-hour window.
            request_key='watchlist-'+str(account_id)+'-'+now.strftime('%Y%m%d%H')+'-'+str(now.minute//15)
            if client:
                env=client(payload)
            else:
                with httpx.Client(timeout=65) as http:
                    response=http.post(PROVIDER_BASE+'/v1/prism/profiles',
                        headers={'x-api-key':api_key,'Accept':'application/json',
                                 'Idempotency-Key':request_key},
                        json=payload)
                response.raise_for_status()
                env=response.json()
            if env.get('success') is False:raise ValueError('SocialCrawl returned an unsuccessful result')
            credits=max(0,int(env.get('credits_used') or 0))
            rows=((env.get('data') or {}).get('results') or [])
            first=rows[0] if rows else {}
            if first.get('status')!='ok':
                message=(first.get('error') or {}).get('message') or first.get('status') or 'No public profile found'
                if credits:LOG.warning('Watchlist provider charged %s credits despite row status %s',credits,first.get('status'))
                raise ValueError(str(message)[:255])
            post_block=first.get('posts') or {}
            if post_block.get('status') in ('failed','deferred','unsupported'):
                raise ValueError('Account profile found, but the posts endpoint returned '+str(post_block.get('status')))
            items=post_block.get('items') or []
            if not isinstance(items,list):items=[]
            from .socialcrawl import _map_result
            from .models import CampaignEvidence
            profile_author=(first.get('data') or {}).get('author') or {}
            profile_handle=str(profile_author.get('username') or '').lstrip('@').casefold() if isinstance(profile_author,dict) else ''
            if profile_handle and profile_handle!=handle:
                raise ValueError('Provider profile identity does not match the registered account handle')
            new_count=0;linked=0;last_post='';skipped_attribution=0
            for raw in items[:20]:
                if not isinstance(raw,dict):continue
                normalized={'platform':platform,**raw}
                mapped=_map_result(db,normalized,default_platform=platform)
                mapped['platform']=platform
                # An Instagram post permalink is not a profile identifier.
                # Resolve source authorship from the provider's POST AUTHOR
                # before any URL-derived or display-name heuristics.
                post_data=raw.get('post') if isinstance(raw.get('post'),dict) else raw
                author_data=post_data.get('author') if isinstance(post_data,dict) else None
                author_data=author_data if isinstance(author_data,dict) else {}
                actual_author=str(author_data.get('username') or
                    author_data.get('handle') or post_data.get('username') or
                    post_data.get('handle') or '').strip().lstrip('@').casefold()
                # A source-authored handle that conflicts with the monitored
                # profile must never be rewritten into a candidate-owned post.
                if actual_author and actual_author!=handle:
                    skipped_attribution+=1
                    continue
                if not actual_author and profile_handle!=handle:
                    skipped_attribution+=1
                    continue
                mapped['observed_handle']='@'+handle
                mapped['author_name']=mapped['author_name'] or profile_handle or handle
                url=mapped['canonical_url']
                if not url and not mapped['provider_result_id']:continue
                # Reuse stored evidence instead of rewriting other collection sources.
                row=(db.query(SocialListeningResult).filter(
                    func.lower(SocialListeningResult.platform)==platform,
                    SocialListeningResult.canonical_url==url).first() if url else None)
                if not row and mapped['provider_result_id']:
                    row=db.query(SocialListeningResult).filter(
                        func.lower(SocialListeningResult.platform)==platform,
                        SocialListeningResult.provider_result_id==mapped['provider_result_id']).first()
                if not row:
                    digest=hashlib.sha256((platform+'|'+(url or mapped['provider_result_id'])).encode()).hexdigest()
                    row=SocialListeningResult(run_id=run.id,provider='SOCIALCRAWL',
                        provider_result_id=mapped['provider_result_id'],platform=platform,
                        content_type=mapped['content_type'],canonical_url=url,
                        author_name=mapped['author_name'],observed_handle='@'+handle,
                        published_at=mapped['published_at'],text_content=mapped['text_content'],
                        language=mapped['language'],relevance_score=mapped['relevance_score'],
                        engagement_json=json.dumps(mapped['engagement']),geography_json='{}',
                        source_identity_json=json.dumps(mapped['source_identity']),
                        watchlist_matches_json=json.dumps([str(watch.id)]),
                        review_state='DISCOVERED',raw_payload_json=json.dumps(raw),
                        content_fingerprint=digest)
                    db.add(row);db.flush();new_count+=1
                if not db.get(WatchlistAccountEvidence,{'account_id':account.id,'result_id':row.id}):
                    db.add(WatchlistAccountEvidence(account_id=account.id,result_id=row.id));linked+=1
                if campaign_id is not None and not db.query(CampaignEvidence.id).filter(
                    CampaignEvidence.campaign_id==campaign_id,
                    CampaignEvidence.result_id==row.id).first():
                    db.add(CampaignEvidence(campaign_id=campaign_id,
                        result_id=row.id,match_method='WATCHLIST_ACCOUNT'))
                    db.flush()
                if not last_post:last_post=mapped['provider_result_id'] or url
            run.status='COMPLETED';run.credits_used=credits
            run.credits_remaining=int(env.get('credits_remaining') or 0)
            run.provider_request_id=str(env.get('request_id') or '')
            run.result_count=linked
            if skipped_attribution:
                LOG.warning('Skipped %s returned posts with unverified authorship for account %s',
                            skipped_attribution,account_id)
            db.add(SocialListeningProviderUsage(provider='SOCIALCRAWL',
                endpoint='/v1/prism/profiles?include=posts',
                provider_request_id=run.provider_request_id,credits_used=credits,
                credits_remaining=run.credits_remaining,cached=False,
                result_count=linked,user_id='watchlist-auto'))
            state=db.get(WatchlistAccountSync,account_id)
            state.state='WAITING';state.last_checked_at=now
            state.next_check_at=now+timedelta(minutes=interval_minutes())
            state.started_at=None;state.last_error='';state.last_credits=credits
            state.last_new_posts=linked;state.total_posts=(state.total_posts or 0)+linked
            if last_post:state.last_post_id=last_post
            db.commit()
            return {'status':'COMPLETED','new_posts':linked,'credits_used':credits}
        except Exception as exc:
            db.rollback()
            row=db.get(WatchlistAccountSync,account_id)
            if row:
                fatal='unsupported' in str(exc).lower()
                row.state='UNSUPPORTED' if fatal else 'ERROR'
                row.started_at=None
                row.last_checked_at=now
                row.next_check_at=None if fatal else now+timedelta(minutes=30)
                row.last_error=str(exc)[:350]
            db.add(SocialListeningProviderUsage(provider='SOCIALCRAWL',
                endpoint='/v1/prism/profiles?include=posts',credits_used=credits,
                result_count=0,user_id='watchlist-auto'))
            failed=db.get(SocialListeningRun,run.id)
            if failed:failed.status='FAILED';failed.error_text=str(exc)[:350];failed.credits_used=credits
            db.commit()
            LOG.exception('Watchlist account sync failed for account id %s',account_id)
            return {'status':'ERROR','error':str(exc)[:350]}
    finally:db.close()

def run_due_cycle():
    db=SessionLocal()
    try:
        ensure_rows(db)
        now=datetime.utcnow()
        due=[row[0] for row in db.query(WatchlistAccountSync.account_id).filter(
            or_(WatchlistAccountSync.next_check_at.is_(None),
                WatchlistAccountSync.next_check_at<=now),
            WatchlistAccountSync.state.in_(['PENDING','WAITING','ERROR','BUDGET_PAUSED'])).order_by(
            WatchlistAccountSync.next_check_at).limit(50).all()]
    finally:db.close()
    for account_id in due:
        try:sync_account(account_id)
        except Exception:LOG.exception('Uncaught watchlist sync failure')
