"""Permission-scoped, read-only Executive Intelligence Command Center.

Derived entirely from existing campaign evidence, assessments, reviews,
watchlists and linked account posts. No paid provider or AI calls.
"""
import json
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from sqlalchemy import and_, func
from .access import allowed, has
from .geography import province_code_for, province_name_for, PROVINCES, INDONESIAN_PROVINCE_ALIASES

def _province_name(code):
    names=INDONESIAN_PROVINCE_ALIASES.get(str(code),[])
    return names[0] if names else province_name_for(code)
from .issue_signals import validated_issue_signals, phrase_screening_candidates
from .models import (MonitoringCampaign, CampaignEvidence, EvidenceAssessment,
    EvidenceReview, SocialListeningResult, IssueCategory, IssueCategoryPhrase,
    WatchlistItem, SourceAccount, WatchlistAccountEvidence, WatchlistAccountSync, IntelligenceItem)
from .socialcrawl import _result_in_scope

def _as_list(raw):
    try:
        value=json.loads(raw or '[]')
        return value if isinstance(value,list) else []
    except (TypeError, ValueError):
        return []

def _period(data):
    today=datetime.utcnow().date()
    preset=str(data.get('period') or '7d')
    if preset not in ('today','7d','30d','custom'):
        raise ValueError('Unknown date range')
    if preset=='custom':
        try:
            start=date.fromisoformat(str(data.get('date_from') or ''))
            end=date.fromisoformat(str(data.get('date_to') or ''))
        except ValueError:
            raise ValueError('A custom range requires two valid dates')
    else:
        days={'today':1,'7d':7,'30d':30}[preset]
        start=today-timedelta(days=days-1);end=today
    if start>end or (end-start).days>366 or end>today:
        raise ValueError('Date range must be valid, no more than 367 days, and not in the future')
    return start.isoformat(),end.isoformat(),preset

def _day(value):
    raw=str(value or '')[:10]
    try:return date.fromisoformat(raw).isoformat()
    except (ValueError,TypeError):return ''

def _scope(p,data):
    selected=str(data.get('province') or '').strip()
    scope=p.get('geographic_scope')
    if scope=='Nationwide':
        if selected and not province_code_for(selected):
            raise ValueError('Unknown province')
        return selected, 'Nationwide' if not selected else _province_name(province_code_for(selected))
    assigned=str(p.get('province') or '').strip()
    assigned_code=province_code_for(assigned,p.get('province_code'))
    if not assigned_code:
        raise PermissionError('Geographic assignment is not configured')
    if selected and province_code_for(selected)!=assigned_code:
        raise PermissionError('Province is outside your authorized scope')
    label=', '.join(x for x in (p.get('regency_city'),p.get('province')) if x) if scope=='Regency/City' else assigned
    return assigned,label

def _region_code(c):
    # A monitoring campaign's targeted region is NOT proof of the post's origin.
    return province_code_for(c.province)

def _briefing(relevant, alerts, waiting, provinces, watch_count, from_day, to_day):
    if not relevant and not alerts:
        return {'text':'No AI-assessed relevant campaign evidence was available for this period and authorized monitoring scope. This does not mean no electoral issues occurred.',
                'kind':'DATA_COVERAGE_NOTICE','sources':[], 'limitation':'Unassessed and uncollected posts are not represented.'}
    parts=[str(len(relevant))+' distinct AI-assessed relevant mention'+('s' if len(relevant)!=1 else '')+' were available for this period.']
    if alerts:
        kinds=Counter(a['category'] for a in alerts)
        top=', '.join(k for k,_ in kinds.most_common(2))
        parts.append(str(len(alerts))+' preliminary issue alert'+('s' if len(alerts)!=1 else '')+' need'+('' if len(alerts)!=1 else 's')+' attention, including '+top+'.')
    else:
        parts.append('No preliminary issue alerts were identified among the assessed relevant records in scope.')
    if waiting:
        parts.append(str(waiting)+' alert'+('s' if waiting!=1 else '')+' await'+('' if waiting!=1 else 's')+' human review.')
    if provinces:
        parts.append('The highest volume of scoped assessed mentions is associated with '+provinces[0]['province']+' monitoring campaigns; this does not identify the authors\' locations.')
    if watch_count:
        parts.append(str(watch_count)+' captured Watchlist post'+('s' if watch_count!=1 else '')+' were linked to monitored accounts in the period.')
    return {'text':' '.join(parts),'kind':'EVIDENCE_DERIVED_BRIEFING',
            'sources':[{'campaign_id':r['campaign_id'],'result_id':r['result_id']} for r in (alerts[:3] or relevant[:3])],
            'limitation':'Compiled from stored AI assessments, not a comprehensive analysis of all crawled conversations. No new generative AI request was made.'}

def build_command_center(db,p,data=None):
    if not has(p,'view_intelligence'):
        raise PermissionError('View intelligence permission required')
    data=data if isinstance(data,dict) else {}
    start,end,preset=_period(data)
    selected,scope_label=_scope(p,data)
    selected_code=province_code_for(selected)
    campaigns=[c for c in db.query(MonitoringCampaign).all() if allowed(p,c)]
    if selected_code:
        campaigns=[c for c in campaigns if _region_code(c)==selected_code]
    campaigns_by_id={c.id:c for c in campaigns}
    campaigns_ids=list(campaigns_by_id)
    # Latest version per (campaign, source), avoiding inflation from reassessment.
    assessed_rows=[]
    if campaigns_ids:
        latest=(db.query(EvidenceAssessment.campaign_id.label('cid'),
                         EvidenceAssessment.result_id.label('rid'),
                         func.max(EvidenceAssessment.assessment_version).label('ver'))
                .filter(EvidenceAssessment.campaign_id.in_(campaigns_ids))
                .group_by(EvidenceAssessment.campaign_id,EvidenceAssessment.result_id)
                .subquery())
        assessed_rows=(db.query(EvidenceAssessment,SocialListeningResult)
            .join(latest,and_(EvidenceAssessment.campaign_id==latest.c.cid,
                              EvidenceAssessment.result_id==latest.c.rid,
                              EvidenceAssessment.assessment_version==latest.c.ver))
            .join(SocialListeningResult,SocialListeningResult.id==EvidenceAssessment.result_id)
            .join(CampaignEvidence,and_(CampaignEvidence.campaign_id==EvidenceAssessment.campaign_id,
                                        CampaignEvidence.result_id==EvidenceAssessment.result_id))
            .filter(func.substr(SocialListeningResult.published_at,1,10)>=start,
                    func.substr(SocialListeningResult.published_at,1,10)<=end)
            .order_by(EvidenceAssessment.created_at.desc(),EvidenceAssessment.id.desc()).all())
    categories=db.query(IssueCategory).filter(IssueCategory.active.is_(True)).all()
    category_names={row.id:row.name for row in categories}
    phrases=db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.active.is_(True)).all()
    relevant={}
    alerts_by_post={}
    region_posts=defaultdict(set)
    region_flags=defaultdict(set)
    unknown_posts=set()
    evidence_checked=0
    source_updated=None
    for assessment,post in assessed_rows:
        campaign=campaigns_by_id[assessment.campaign_id]
        if not _result_in_scope(db,p,post):continue
        evidence_checked+=1
        if source_updated is None or post.collected_at and post.collected_at>source_updated:
            source_updated=post.collected_at
        if str(assessment.relevance_label or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
            continue
        note={'result_id':str(post.id),'campaign_id':str(campaign.id),
              'campaign_name':campaign.name,'source_url':post.canonical_url,
              'platform':post.platform,'author':post.author_name or post.observed_handle or 'Unknown author',
              'published_at':post.published_at,'detected_at':assessment.created_at.isoformat() if assessment.created_at else None,
              'summary':(assessment.explanation or post.text_content or '').strip()[:260],
              'relevance_label':assessment.relevance_label}
        relevant.setdefault(post.id,note)
        code=_region_code(campaign)
        if code:region_posts[code].add(post.id)
        else:unknown_posts.add(post.id)
        explicit=validated_issue_signals(_as_list(assessment.potential_issue_signals_json),
                                         category_names,post.text_content)
        if not explicit:
            explicit=phrase_screening_candidates(post.text_content,categories,phrases)
        if not explicit:continue
        # Same review states and validated issue candidates used by Intelligence Inbox.
        review=(db.query(EvidenceReview).join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
                .filter(EvidenceAssessment.campaign_id==campaign.id,
                        EvidenceAssessment.result_id==post.id,
                        EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
                .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).first())
        decision=review.decision if review else 'AWAITING_REVIEW'
        if decision=='FLAG_DISMISSED':continue
        signal=explicit[0]
        if code:region_flags[code].add(post.id)
        candidate=_as_list(assessment.candidate_signals_json)
        candidate_name=''
        if candidate:
            first=candidate[0]
            candidate_name=str(first.get('name') or first.get('value') or '') if isinstance(first,dict) else str(first)
        alert={**note,'category':signal['category_name'],'evidence_quote':signal.get('evidence_quote','')[:280],
               'description':signal.get('explanation') or note['summary'],
               'candidate':candidate_name[:120], 'province':_province_name(code) if code else 'Unknown / Unclassified',
               'province_basis':'CAMPAIGN_MONITORING_SCOPE' if code else 'UNCLASSIFIED',
               'review_status':decision,
               'signal_provenance':signal.get('signal_provenance',''),
               'priority':'Review now' if decision=='FURTHER_INVESTIGATION' else 'Awaiting review',
               'priority_order':3 if decision=='FURTHER_INVESTIGATION' else 2 if decision=='FLAG_CONFIRMED' else 1}
        prior=alerts_by_post.get(post.id)
        if prior is None or alert['priority_order']>prior['priority_order']:
            alerts_by_post[post.id]=alert
    alerts=list(alerts_by_post.values())
    alerts.sort(key=lambda a:(a['priority_order'],a['detected_at'] or ''),reverse=True)
    by_region=[{'province':_province_name(code),'count':len(posts),
                'flagged':len(region_flags.get(code,set())),
                'province_code':code} for code,posts in region_posts.items()]
    by_region.sort(key=lambda r:(r['flagged'],r['count']),reverse=True)
    # Combine assessed social posts with traditional/manual Intelligence Inbox
    # records. These are presented as recent records, NOT counted again in
    # the distinct AI-assessed social indicators above.
    manual_recent=[]
    for record in db.query(IntelligenceItem).all():
        if not allowed(p,record):continue
        if selected_code and province_code_for(record.province,record.province_code)!=selected_code:
            continue
        date_text=record.publication_datetime or record.publication_date or ''
        display_date=date_text if _day(date_text) else record.created_at.isoformat() if record.created_at else ''
        if not start<=_day(display_date)<=end:continue
        manual_recent.append({
            'record_type':'INTELLIGENCE_ITEM','id':str(record.id),
            'campaign_name':record.intelligence_id or 'Intelligence Inbox record',
            'platform':record.platform or record.source_type or 'Recorded source',
            'author':record.observed_publisher_handle or record.author or record.source_name or 'Unknown source',
            'source_url':record.source_url,
            'published_at':display_date,
            'summary':(record.ai_summary or record.title or record.original_content or '').strip()[:260],
            'review_status':record.review_status,
            'date_basis':'SOURCE_PUBLICATION' if _day(date_text) else 'RECORD_CREATED'
        })
    recent=sorted(list(relevant.values())+manual_recent,
                  key=lambda x:x['published_at'] or '',reverse=True)[:5]
    # Watchlist highlights use only evidence explicitly linked to registered
    # accounts, not noisy substring matches against people's names.
    watch_items=[w for w in db.query(WatchlistItem).all() if allowed(p,w)]
    if selected_code:
        watch_items=[w for w in watch_items if province_code_for(w.province)==selected_code]
    watch_rows=[];watch_count_ids=set()
    if watch_items:
        ids=[w.id for w in watch_items]
        joined=(db.query(WatchlistItem,SourceAccount,WatchlistAccountEvidence,SocialListeningResult)
            .join(SourceAccount,SourceAccount.watchlist_id==WatchlistItem.id)
            .join(WatchlistAccountEvidence,WatchlistAccountEvidence.account_id==SourceAccount.id)
            .join(SocialListeningResult,SocialListeningResult.id==WatchlistAccountEvidence.result_id)
            .filter(WatchlistItem.id.in_(ids),
                    func.substr(SocialListeningResult.published_at,1,10)>=start,
                    func.substr(SocialListeningResult.published_at,1,10)<=end)
            .order_by(SocialListeningResult.published_at.desc(),SocialListeningResult.id.desc()).yield_per(200))
        seen_watch=set()
        for w,account,edge,post in joined:
            if not _result_in_scope(db,p,post):continue
            watch_count_ids.add(post.id)
            if w.id in seen_watch or len(watch_rows)>=5:continue
            seen_watch.add(w.id)
            watch_rows.append({'watchlist_id':str(w.id),'name':w.name,'province':w.province or 'Unclassified',
                'platform':post.platform,'handle':account.handle,'last_post_at':post.published_at,
                'last_post_url':post.canonical_url,'summary':(post.text_content or '')[:170]})
            # Keep scanning to count all scoped linked posts, not only highlights.
    briefing=_briefing(list(relevant.values()),alerts,
                       sum(a['review_status']=='AWAITING_REVIEW' for a in alerts),
                       by_region,len(watch_count_ids),start,end)
    return {'period':{'preset':preset,'date_from':start,'date_to':end},
            'available_provinces':[{'name':_province_name(row['code']),'code':str(row['code'])} for row in PROVINCES] if p.get('geographic_scope')=='Nationwide' else [{'name':scope_label,'code':province_code_for(selected)}],
            'scope':{'label':scope_label,'geographic_scope':p.get('geographic_scope'),
                     'selected_province':selected,'can_select_national':p.get('geographic_scope')=='Nationwide'},
            'generated_at':datetime.utcnow().isoformat()+'Z',
            'latest_evidence_at':source_updated.isoformat()+'Z' if source_updated else None,
            'indicators':{'relevant_mentions':len(relevant),
                'potential_alerts':len(alerts),
                'awaiting_review':sum(x['review_status']=='AWAITING_REVIEW' for x in alerts),
                'emerging_issues':None},
            'briefing':briefing,'alerts':alerts[:5], 'latest_intelligence':recent,
            'regions':by_region[:38],
            'unknown_region_mentions':len(unknown_posts),
            'region_method':'CAMPAIGN_MONITORING_SCOPE_NOT_POST_ORIGIN',
            'watchlist':{'entries':watch_rows,'captured_posts_in_period':len(watch_count_ids),
                         'monitored_profiles':len(watch_items)},
            'coverage':{'assessed_pairs_in_period':evidence_checked,'relevant_distinct_posts':len(relevant),
                        'distinct_campaigns_in_scope':len(campaigns_by_id),
                        'warning':'Only AI-assessed, campaign-linked posts meeting the current filters are counted. Most stored posts may not yet have assessments. Province indicates monitoring scope, not verified author location.'},
            'capabilities':{'emerging_issues':False,'ai_generated_new_summary':False,
                            'cross_module_assistant':False},
            'paid_provider_called':False}
