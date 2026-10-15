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
