"""Conservative application-side collection limits; no paid calls or schema changes.

Prism background runs may collect more rows upstream than the requested
delivery limit. The monthly guard counts reported provider rows where known,
and reserves the bounded local candidate allowance otherwise. It is not a
provider-side hard limit on upstream crawled rows.
"""
import json
import os
from datetime import datetime,timezone
from sqlalchemy import func,text
from .models import SocialListeningRun,SocialListeningResult,SocialListeningProviderUsage

MONTHLY_LIMIT=3_000_000
STORAGE_LIMIT=6_000_000
LOCK_KEY=1819001

def lock(db):
    if db.get_bind().dialect.name=='postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':LOCK_KEY})

def nonnegative(value):
    return value if type(value) is int and value>=0 else 0

def cap(name,maximum):
    try:return max(0,min(maximum,int(os.getenv(name,str(maximum)))))
    except (TypeError,ValueError):return 0

def meta_for(run):
    try:value=json.loads(run.query_json or '{}')
    except (TypeError,ValueError):return {}
    return value if isinstance(value,dict) else {}

def snapshot(db,now=None,exclude_run_id=None):
    now=now or datetime.now(timezone.utc).replace(tzinfo=None)
    month=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    monthly_cap=cap('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT',MONTHLY_LIMIT)
    storage_cap=cap('BAWASLU_ACTIVE_SOURCE_STORAGE_LIMIT',STORAGE_LIMIT)
    # Usage records on the legacy path count delivered/mapped posts; no
    # fabricated upstream count is substituted for missing diagnostics.
    legacy=int(db.query(func.sum(SocialListeningProviderUsage.result_count)).filter(
        SocialListeningProviderUsage.created_at>=month,
        SocialListeningProviderUsage.provider!='SOCIALCRAWL_PRISM').scalar() or 0)
    grouped={};reserved=0;storage_reserved=0;unknown=0
    rows=db.query(SocialListeningRun).filter(SocialListeningRun.provider=='SOCIALCRAWL_PRISM',
        (SocialListeningRun.executed_at>=month)|SocialListeningRun.status.in_(['QUEUED','RUNNING'])).yield_per(200)
    for run in rows:
        if run.id==exclude_run_id:continue
        meta=meta_for(run)
        if meta.get('local_reuse'):continue
        provider=meta.get('provider_diagnostics') or {}
        diag=meta.get('collection_diagnostics') or {}
        if not isinstance(provider,dict):provider={}
        if not isinstance(diag,dict):diag={}
        reported=provider.get('collected')
        known=type(reported) is int and reported>=0
        actual=reported if known else max(nonnegative(diag.get('raw_provider_items')),nonnegative(run.result_count))
        reservation=min(300,max(100,nonnegative((meta.get('body') or {}).get('limit'))))
        active=run.status in ('QUEUED','RUNNING')
        uncertain=bool(meta.get('submission_uncertain'))
        if run.executed_at and run.executed_at>=month:
            key=run.provider_request_id if str(run.provider_request_id or '').startswith('run_') else 'local:'+str(run.id)
            grouped[key]=max(grouped.get(key,0),actual)
            if not known:unknown+=1
            if active or uncertain:reserved+=max(0,reservation-actual)
        if active:storage_reserved+=reservation
    # New legacy runs reserve capacity before dispatch and preserve provider
    # receipt counts even when mapping/storage fails. Existing usage rows retain
    # their historical delivered-result semantics.
    legacy_runs=db.query(SocialListeningRun).filter(SocialListeningRun.provider=='SOCIALCRAWL',
        (SocialListeningRun.executed_at>=month)|SocialListeningRun.status.in_(['QUEUED','RUNNING'])).yield_per(200)
    for run in legacy_runs:
        if run.id==exclude_run_id:continue
        info=meta_for(run).get('legacy_collection')
        if not isinstance(info,dict):continue
        actual=nonnegative(info.get('observed_rows'));mapped=nonnegative(info.get('ledger_mapped'))
        allowance=nonnegative(info.get('reserved_posts'))
        active=run.status in ('QUEUED','RUNNING')
        if run.executed_at and run.executed_at>=month:
            # The legacy ledger already counts mapped rows.
            legacy+=max(0,actual-mapped)
            if active or info.get('submission_uncertain'):reserved+=max(0,allowance-actual)
        if active:storage_reserved+=allowance
    stored=int(db.query(func.count(SocialListeningResult.id)).scalar() or 0)
    used=legacy+sum(grouped.values())
    return {'monthly_limit':monthly_cap,'monthly_counted':used,'monthly_reserved':reserved,
            'storage_limit':storage_cap,'stored_source_rows':stored,'storage_reserved':storage_reserved,
            'runs_without_upstream_count':unknown,'count_basis':'REPORTED_PRISM_ROWS_PLUS_LEGACY_LEDGER_AND_RESERVATIONS',
            'monthly_remaining':max(0,monthly_cap-used-reserved),
            'storage_remaining':max(0,storage_cap-stored-storage_reserved)}

def legacy_requested(filters):
    platforms=filters.get('platforms') or []
    return max(1,min(200,int(filters.get('limit',50))))*max(1,len(platforms))


def assert_capacity(db,requested,exclude_run_id=None):
    value=snapshot(db,exclude_run_id=exclude_run_id)
    if requested>value['monthly_remaining']:raise ValueError('Monthly collection allowance reached; no additional paid collection was started')
    if requested>value['storage_remaining']:raise ValueError('Active source storage allowance reached; no additional paid collection was started')
    return value

def assert_storage(db,requested,exclude_run_id=None):
    value=snapshot(db,exclude_run_id=exclude_run_id)
    if requested>value['storage_remaining']:raise ValueError('Active source storage allowance reached; existing provider results can be recovered after capacity is available')
    return value
