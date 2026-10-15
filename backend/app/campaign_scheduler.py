"""Build 64.3 — read-only crawl planning and metering.

No timer, outbound client, or paid task can be activated from this module.
All budgets default to zero unless an authorized future deployment explicitly
sets them. Planning only reads usage and campaign configuration.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from .models import (MonitoringCampaign, CampaignRun, SocialListeningRun,
                     SocialListeningProviderUsage)
from .socialcrawl import estimate_search_cost

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def campaign_query(c):
    keywords=json.loads(c.primary_keywords_json or '[]')
    excluded=json.loads(c.excluded_keywords_json or '[]')
    # A provider-agnostic query until syntax/OR behavior is validated.
    # Don't treat these terms as proof of contextual relevance.
    return {
        'query':' '.join(keywords),
        'exclude_terms':excluded,
        'platforms':json.loads(c.platforms_json or '[]'),
        'language':c.language or '',
        'date_from':c.date_from or '',
        'date_to':c.date_to or '',
        'province':c.province or '',
        'regency_city':c.regency_city or '',
        'limit':50,
    }

def _budget_env(name):
    value=os.getenv(name,'0')
    try:
        amount=int(value)
    except (TypeError,ValueError):
        return 0
    return max(0,amount)

def used_credits_24h(db,now):
    earliest=now-timedelta(hours=24)
    # Includes manual queries as well as other campaigns, preventing an
    # accidental overestimate of available platform credits.
    val=db.query(func.sum(SocialListeningProviderUsage.credits_used)).filter(
        SocialListeningProviderUsage.created_at>=earliest
    ).scalar()
    return max(0,int(val or 0))

def campaign_schedule_preview(db,c,now=None):
    now=now or utc_now()
    estimate=estimate_search_cost(campaign_query(c))
    credits=int(estimate['estimated_credits'])
    used=used_credits_24h(db,now)
    daily=_budget_env('BAWASLU_CRAWL_DAILY_CREDIT_BUDGET')
    per_run=_budget_env('BAWASLU_CRAWL_PER_RUN_CREDIT_LIMIT')
    # Hard global block; explicit deployment review required to change code.
    allowed_paid=False
    reasons=[]
    if c.status != 'ACTIVE': reasons.append('Campaign not activated')
    if not allowed_paid: reasons.append('Automatic paid crawling disabled pending explicit approval')
    if daily <= 0 or per_run <= 0: reasons.append('Automatic credit budgets are set to zero')
    if credits > per_run and per_run > 0: reasons.append('Estimated run cost exceeds per-run budget')
    if used+credits > daily and daily > 0: reasons.append('Estimated cost exceeds 24-hour credit budget')
    due_at=c.next_run_at
    if due_at is None and c.status=='ACTIVE':
        due_at=c.last_success_at or c.created_at
        if due_at: due_at=due_at+timedelta(minutes=c.interval_minutes)
    return {
        'campaign_id':str(c.id),'campaign_status':c.status,
        'last_crawled_at':c.last_success_at.isoformat() if c.last_success_at else None,
        'next_crawl_at':due_at.isoformat() if due_at and c.status=='ACTIVE' else None,
        'is_due':bool(due_at and due_at<=now and c.status=='ACTIVE'),
        'estimated_credits_per_run':credits,
        'estimated_components':estimate['components'],
        'credits_used_last_24h':used,
        'daily_credit_budget':daily,'per_run_credit_limit':per_run,
        'credits_available_in_budget':max(0,daily-used),
        'automatic_paid_crawling_enabled':False,
        'can_run_paid':False,'blocked_reasons':reasons,
        'scheduler_status':'DISABLED' if c.status not in ('PAUSED',) else 'PAUSED',
        'interval_minutes':c.interval_minutes,
    }

def campaign_history(db,c,limit=20):
    edges=db.query(CampaignRun).filter(CampaignRun.campaign_id==c.id).order_by(
        CampaignRun.created_at.desc(),CampaignRun.id.desc()
    ).limit(max(1,min(limit,50))).all()
    items=[]
    for edge in edges:
        run=db.get(SocialListeningRun,edge.social_listening_run_id)
        if not run: continue
        items.append({'id':str(edge.id),'run_id':str(run.id),
            'executed_at':run.executed_at.isoformat(),
            'status':run.status,'triggered_by':edge.triggered_by,
            'credits_used':run.credits_used,'result_count':run.result_count,
            'error':run.error_text or ''})
    return items

def keyword_screen(c,row):
    """Literal OR for main keywords; secondary terms add context, never gate.

    All assessments remain preliminary, not findings of violations.
    Source evidence is retained separately by the collection pipeline.
    """
    raw=row.get('raw') or {}
    comments=raw.get('comments') if isinstance(raw,dict) else None
    comment_text=''
    if isinstance(comments,list):
        comment_text=' '.join(str(x.get('text') or '') for x in comments if isinstance(x,dict))
    haystack=((row.get('text_content') or '')+' '+comment_text).casefold()
    primary=json.loads(c.primary_keywords_json or '[]')
    secondary=json.loads(c.secondary_keywords_json or '[]')
    excluded=json.loads(c.excluded_keywords_json or '[]')
    matched_main=[word for word in primary if word.casefold() in haystack]
    matched_secondary=[word for word in secondary if word.casefold() in haystack]
    matched_excluded=[word for word in excluded if word.casefold() in haystack]
    return {'matched':bool(matched_main) and not bool(matched_excluded),
            'main_keywords':matched_main,'secondary_keywords':matched_secondary,
            'excluded_keywords':matched_excluded,
            'context_signal':'STRONGER_CONTEXT' if matched_secondary and matched_main else
                             'MAIN_KEYWORD_ONLY' if matched_main else 'NO_MAIN_KEYWORD'}

def _keyword_match(c,row):
    return keyword_screen(c,row)['matched']

def simulate_campaign_cycle(db,p,c,provider_client=None,now=None,daily_budget=0,per_run_limit=0):
    """Exercise scheduled collection with an injected fake provider only.

    NOT an HTTP endpoint or background job. Never accepts the real network
    provider; budgets are explicit test inputs, default-deny. Production paid
    crawling remains blocked until a separately approved execution design.
    """
    if provider_client is None or not callable(provider_client):
        raise ValueError('Simulated scheduler requires an injected test provider')
    from .access import allowed, has
    from .socialcrawl import (_scope_filters, execute_search, _extract_items,
                              _map_result, _matches_local_filters, _result_in_scope)
    from .models import CampaignEvidence, SocialListeningResult
    from sqlalchemy import func

    if not has(p,'view_intelligence') or not allowed(p,c):
        raise PermissionError('Campaign is outside authorized access')
    if str(c.created_by)!=str(p.get('id')) and not (
        p.get('role')=='National Administrator' and has(p,'administration')
    ): raise PermissionError('Campaign owner or national administrator required')
    if c.status!='ACTIVE':
        return {'status':'SKIPPED','reason':'Campaign is not active'}
    now=now or utc_now()
    due=c.next_run_at or c.created_at+timedelta(minutes=c.interval_minutes)
    if due and due>now:
        return {'status':'SKIPPED','reason':'Not due','next_run_at':due.isoformat()}
    filters=_scope_filters(p,campaign_query(c))
    estimate=estimate_search_cost(filters)['estimated_credits']
    recent=used_credits_24h(db,now)
    if (type(per_run_limit) is not int or type(daily_budget) is not int
        or per_run_limit<1 or daily_budget<1
        or estimate>per_run_limit or recent+estimate>daily_budget):
        return {'status':'BLOCKED','reason':'Credit budget unavailable',
                'estimated_credits':estimate,'credits_used_last_24h':recent}
    previous_id=db.query(func.max(SocialListeningRun.id)).scalar() or 0
    envelope=[]
    def capture(scoped):
        response=provider_client(scoped)
        envelope.append(response)
        return response
    error=None
    result=None
    try:
        result=execute_search(db,p,filters,provider_client=capture)
    except Exception as exc:
        error=str(exc)[:160]
    if result:
        run=db.get(SocialListeningRun,int(result['run']['id']))
    else:
        # This is only safe in a single-worker synthetic test environment.
        run=db.query(SocialListeningRun).filter(
            SocialListeningRun.id>previous_id,
            SocialListeningRun.executed_by==str(p['id'])
        ).order_by(SocialListeningRun.id.desc()).first()
    if not run:
        raise RuntimeError('Synthetic provider attempt did not create a run record')
    edge=CampaignRun(campaign_id=c.id,social_listening_run_id=run.id,triggered_by='SIMULATED')
    db.add(edge)
    new_links=0
    if result and envelope:
        env=envelope[-1]
        for raw in _extract_items(env):
            if not isinstance(raw,dict): continue
            mapped=_map_result(db,raw,default_platform='online_news' if
                json.loads(c.platforms_json or '[]')==['online_news'] else '')
            screen=keyword_screen(c,mapped)
            if not screen['matched'] or not _matches_local_filters(mapped,filters): continue
            row=db.query(SocialListeningResult).filter(
                SocialListeningResult.content_fingerprint==mapped['content_fingerprint']
            ).order_by(SocialListeningResult.id.asc()).first()
            if not row or not _result_in_scope(db,p,row): continue
            prior=db.query(CampaignEvidence).filter(
                CampaignEvidence.campaign_id==c.id,
                CampaignEvidence.result_id==row.id).first()
            if not prior:
                db.add(CampaignEvidence(campaign_id=c.id,result_id=row.id,
                    match_method='KEYWORD',matched_fields_json=json.dumps({
                        'field':'text_content','main_keywords':screen['main_keywords'],
                        'secondary_keywords':screen['secondary_keywords'],
                        'context_signal':screen['context_signal']},ensure_ascii=False)))
                new_links+=1
    if error:
        # Retried later at bounded intervals (15, 30, 60 minutes).
        # Count prior consecutive failures, stopping at the last success.
        history=campaign_history(db,c,limit=10)
        failures=0
        for h in history:
            if h['status']!='FAILED': break
            failures+=1
        backoff=min(60,15*(2**min(failures,2)))
        c.next_run_at=now+timedelta(minutes=backoff)
    else:
        c.last_success_at=now
        c.next_run_at=now+timedelta(minutes=c.interval_minutes)
    c.updated_at=now
    db.commit()
    return {'status':'FAILED' if error else 'COMPLETED',
            'run_id':str(run.id),'error':error or '',
            'linked_new_evidence':new_links,
            'credits_used':run.credits_used,
            'next_run_at':c.next_run_at.isoformat()}
