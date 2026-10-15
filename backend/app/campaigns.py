"""Architecture v2 campaign configuration — no paid crawl execution.

A campaign is a persistent plan, distinct from any provider run. All actions
are enforced in the existing authenticated Social Listening API.
"""
import json
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from .models import MonitoringCampaign, CampaignRun, CampaignEvidence
from .access import has, allowed, audit
from .socialcrawl import _scope_filters, AVAILABLE_PLATFORMS

MAX_KEYWORDS=30
MAX_CAMPAIGNS_PER_LIST=200
MAX_NAME=255

def _keywords(value,label,mandatory=False):
    if not isinstance(value,list):
        raise ValueError(label+' must be a list of keywords')
    if len(value)>MAX_KEYWORDS:
        raise ValueError(label+' exceeds 30 keywords')
    found={}
    for entry in value:
        if not isinstance(entry,str):
            raise ValueError(label+' must contain text')
        value=entry.strip()
        if not value or len(value)>120:
            raise ValueError(label+' keywords must be 1–120 characters')
        found.setdefault(value.casefold(),value)
    if mandatory and not found: raise ValueError(label+' requires at least one keyword')
    return list(found.values())

def _iso_date(value,label):
    if not value: return ''
    if not isinstance(value,str): raise ValueError(label+' must be a date')
    try: return date.fromisoformat(value).isoformat()
    except ValueError: raise ValueError(label+' must be YYYY-MM-DD')

def _normalize(db,p,data):
    if not isinstance(data,dict): raise ValueError('Campaign configuration must be an object')
    name=str(data.get('name') or '').strip()
    if not name or len(name)>MAX_NAME: raise ValueError('Campaign name must be 1–255 characters')
    description=str(data.get('description') or '').strip()
    if len(description)>2000: raise ValueError('Campaign description must not exceed 2000 characters')
    primary=_keywords(data.get('primary_keywords',[]),'Main keywords',True)
    secondary=_keywords(data.get('secondary_keywords',[]),'Secondary keywords')
    excluded=_keywords(data.get('excluded_keywords',[]),'Excluded keywords')
    overlap={x.casefold() for x in primary}&{x.casefold() for x in excluded}
    if overlap: raise ValueError('Main keywords cannot also be excluded')
    platforms=data.get('platforms',[])
    if not isinstance(platforms,list) or not platforms: raise ValueError('Select at least one platform')
    if len(platforms)>len(AVAILABLE_PLATFORMS): raise ValueError('Too many platforms')
    platforms=list(dict.fromkeys(platforms))
    if any(not isinstance(x,str) or x not in AVAILABLE_PLATFORMS for x in platforms):
        raise ValueError('Invalid Social Listening platform')
    language=data.get('language','') or ''
    if language not in ('','id','en','ms'): raise ValueError('Unsupported language')
    start=_iso_date(data.get('date_from'),'Start date')
    end=_iso_date(data.get('date_to'),'End date')
    if start and end and start>end: raise ValueError('Start date must be before end date')
    interval=data.get('interval_minutes',180)
    if type(interval) is not int or not 60<=interval<=10080:
        raise ValueError('Monitoring interval must be 60–10080 minutes')
    # Reuse established regional scope validation before persisting.
    filters=_scope_filters(p,{'query':' '.join(primary),'platforms':platforms,
       'province':data.get('province') or '', 'regency_city':data.get('regency_city') or ''})
    return {'name':name,'description':description,
       'primary_keywords_json':json.dumps(primary,ensure_ascii=False),
       'secondary_keywords_json':json.dumps(secondary,ensure_ascii=False),
       'excluded_keywords_json':json.dumps(excluded,ensure_ascii=False),
       'platforms_json':json.dumps(platforms),
       'language':language,'date_from':start,'date_to':end,
       'province':filters.get('province',''),'regency_city':filters.get('regency_city',''),
       'interval_minutes':interval}

def _view(db,c):
    counts=db.query(CampaignRun).filter(CampaignRun.campaign_id==c.id).count()
    evidence=db.query(CampaignEvidence).filter(CampaignEvidence.campaign_id==c.id).count()
    return {'id':str(c.id),'name':c.name,'description':c.description,
       'primary_keywords':json.loads(c.primary_keywords_json or '[]'),
       'secondary_keywords':json.loads(c.secondary_keywords_json or '[]'),
       'excluded_keywords':json.loads(c.excluded_keywords_json or '[]'),
       'platforms':json.loads(c.platforms_json or '[]'),'language':c.language,
       'date_from':c.date_from,'date_to':c.date_to,
       'province':c.province,'regency_city':c.regency_city,
       'interval_minutes':c.interval_minutes,'status':c.status,
       'created_by':c.created_by,
       'next_run_at':c.next_run_at.isoformat() if c.next_run_at else None,
       'last_success_at':c.last_success_at.isoformat() if c.last_success_at else None,
       'run_count':counts,'evidence_count':evidence,
       'created_at':c.created_at.isoformat() if c.created_at else None}

def _editable(p,c):
    if p.get('role')=='National Administrator' and has(p,'administration'): return True
    return c.created_by==p.get('id') and has(p,'add_intelligence')

MANUAL_CRAWL_ESTIMATED_CREDIT_LIMIT=5

def _keyword_search_plan(db,p,c):
    from .campaign_scheduler import campaign_query
    from .socialcrawl import search_preflight
    base=campaign_query(c)
    keywords=json.loads(c.primary_keywords_json or '[]')
    searches=[]
    for keyword in keywords:
        filters={**base,'query':keyword}
        pre=search_preflight(db,p,filters)
        searches.append({'keyword':keyword,'filters':filters,'credits':int(pre['estimated_credits']),
                         'components':pre['components'],'duplicate_recent':pre.get('duplicate_recent')})
    return searches

def _manual_preflight(db,p,c):
    searches=_keyword_search_plan(db,p,c)
    cost=sum(s['credits'] for s in searches)
    return {'estimated_credits':cost,'components':[
                {'label':s['keyword']+': '+part['label'],'credits':part['credits']}
                for s in searches for part in s['components']],
            'duplicate_recent':next((s['duplicate_recent'] for s in searches if s['duplicate_recent']),None),
            'keyword_searches':[{'keyword':s['keyword'],'estimated_credits':s['credits'],
                                 'duplicate_recent':s['duplicate_recent']} for s in searches],
            'credit_limit':MANUAL_CRAWL_ESTIMATED_CREDIT_LIMIT,
            'can_run':bool(cost>0 and cost<=MANUAL_CRAWL_ESTIMATED_CREDIT_LIMIT),
            'manual_only':True,'paid_provider_called':False,'retrieval_mode':'PER_KEYWORD_OR'}

def _existing_thumbnail(item):
    from .socialcrawl import _value
    try: raw=json.loads(item.raw_payload_json or '{}')
    except (ValueError,TypeError): return ''
    url=_value(raw,'post.media.thumbnail_url','post.media.thumbnail','post.media.cover_url',
               'post.video.cover_url','post.thumbnail_url','thumbnail_url','image_url',
               'post.media.0.thumbnail_url','post.media.0.url',default='')
    if isinstance(url,str) and url.startswith('https://') and len(url)<=2048:
        return url
    return ''

def campaign_action(db:Session,p,action,data,id=None):
    if not has(p,'view_intelligence'): raise PermissionError('No intelligence access')
    if action in ('campaignManualPreflight','campaignManualRun'):
        from .campaign_scheduler import campaign_query, keyword_screen
        from .socialcrawl import execute_search
        from .models import SocialListeningResult
        from .socialcrawl import _result_in_scope
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if not _editable(p,c): raise PermissionError('Only campaign owner or national administrator can run collection')
        if c.status!='DRAFT': raise ValueError('Only draft campaigns can be crawled manually')
        preview=_manual_preflight(db,p,c)
        if action=='campaignManualPreflight': return preview
        if not preview['can_run']: raise ValueError('Estimated crawl exceeds the 5-credit manual limit')
        if (data or {}).get('confirm_cost') is not True: raise ValueError('Explicit credit confirmation required')
        if int((data or {}).get('confirmed_credits',-1))!=preview['estimated_credits']:
            raise ValueError('Credit estimate changed; request a new preview')
        if preview['duplicate_recent'] and (data or {}).get('acknowledge_duplicate') is not True:
            raise ValueError('Recent duplicate search requires acknowledgement')
        runs=[]; linked=0; new_results=0; credits_used=0
        # Independent searches ensure each main keyword can retrieve content.
        # Existing fingerprints and CampaignEvidence uniqueness deduplicate overlap.
        for search in _keyword_search_plan(db,p,c):
            response=execute_search(db,p,search['filters'],confirmed_cost=True)
            run_id=int(response['run']['id'])
            runs.append(response['run'])
            credits_used+=int(response['run'].get('credits_used') or 0)
            new_results+=len(response.get('results') or [])
            db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=run_id,triggered_by='MANUAL'))
            for item in response.get('results') or []:
                row=db.get(SocialListeningResult,int(item['id']))
                if not row or not _result_in_scope(db,p,row): continue
                match=keyword_screen(c,{'text_content':row.text_content,
                                        'raw':json.loads(row.raw_payload_json or '{}')})
                if not match['matched']: continue
                existing=db.query(CampaignEvidence).filter_by(campaign_id=c.id,result_id=row.id).first()
                if existing: continue
                db.add(CampaignEvidence(campaign_id=c.id,result_id=row.id,
                      matched_fields_json=json.dumps(match,ensure_ascii=False)))
                linked+=1
            db.commit()
        c.last_success_at=datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        audit(db,p,'MonitoringCampaign',c.id,'CAMPAIGN_MANUAL_CRAWL',{'runs':{'new':len(runs)},'linked_evidence':{'new':linked}})
        return {'runs':runs,'run':runs[-1],'linked_evidence':linked,'result_count':new_results,
                'credits_used':credits_used,'manual_only':True,'estimated_credits':preview['estimated_credits'],
                'retrieval_mode':'PER_KEYWORD_OR'}
    if action=='campaignDashboard':
        from collections import Counter
        from .models import SocialListeningResult
        from .socialcrawl import _result_in_scope
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        from_day=_iso_date((data or {}).get('date_from'),'Date from')
        to_day=_iso_date((data or {}).get('date_to'),'Date to')
        if from_day and to_day and from_day>to_day: raise ValueError('Date from cannot be after date to')
        links=db.query(CampaignEvidence).filter(CampaignEvidence.campaign_id==c.id).order_by(CampaignEvidence.id.desc()).limit(5000).all()
        platforms=Counter(); main=Counter(); secondary=Counter(); states=Counter(); daily=Counter(); daily_types={}; sentiment=Counter()
        visible=0
        for link in links:
            item=db.get(SocialListeningResult,link.result_id)
            if not item or not _result_in_scope(db,p,item): continue
            source_day=str(item.published_at or '')[:10]
            try: source_day=date.fromisoformat(source_day).isoformat()
            except ValueError: source_day=''
            if (from_day or to_day) and (not source_day or (from_day and source_day<from_day) or (to_day and source_day>to_day)): continue
            visible+=1
            if source_day: daily[source_day]+=1
            platforms[item.platform or 'unknown']+=1
            content_kind='comments' if 'comment' in str(item.content_type or '').casefold() else 'posts'
            if source_day:
                daily_types.setdefault(source_day,{'posts':0,'comments':0})[content_kind]+=1
            sentiment['Unclassified']+=1
            states[item.review_state or 'UNKNOWN']+=1
            try: matched=json.loads(link.matched_fields_json or '{}')
            except (ValueError,TypeError): matched={}
            if isinstance(matched,dict):
                for word in set(matched.get('main_keywords') or []): main[str(word)]+=1
                for word in set(matched.get('secondary_keywords') or []): secondary[str(word)]+=1
        runs=db.query(CampaignRun).filter(CampaignRun.campaign_id==c.id).count()
        return {'campaign_id':str(c.id),'evidence_count':visible,'run_count':runs,
                'platforms':dict(platforms),'review_states':dict(states),
                'daily_trend':[{ 'date':day,'count':daily[day],**daily_types.get(day,{'posts':0,'comments':0})} for day in sorted(daily)],
                'sentiment':dict(sentiment),'sentiment_method':'UNCLASSIFIED',
                'date_from':from_day,'date_to':to_day,
                'main_keywords':dict(main),'secondary_keywords':dict(secondary),
                'limited_to':5000,'truncated':len(links)==5000,
                'paid_provider_called':False}
    if action=='campaignRunReadiness':
        # Dry-run only: calculate scoped cost and duplicate warnings without invoking a provider.
        from .campaign_scheduler import campaign_query, campaign_schedule_preview
        from .socialcrawl import search_preflight
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if not _editable(p,c): raise PermissionError('Only campaign owner or national administrator can preview execution')
        preflight=search_preflight(db,p,campaign_query(c))
        schedule=campaign_schedule_preview(db,c)
        return {'campaign_id':str(c.id),'estimated_credits':preflight['estimated_credits'],
                'components':preflight['components'],
                'duplicate_recent':preflight.get('duplicate_recent'),
                'credits_used_last_24h':schedule['credits_used_last_24h'],
                'blocked_reasons':schedule['blocked_reasons'],
                'can_execute':False,'paid_provider_called':False,
                'notice':'Preview only. Campaign execution is disabled until a separate authorized release.'}
    if action=='campaignEvidence':
        from .models import SocialListeningResult
        from .socialcrawl import _result_in_scope
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        links=db.query(CampaignEvidence).filter(CampaignEvidence.campaign_id==c.id).order_by(CampaignEvidence.added_at.desc(),CampaignEvidence.id.desc()).limit(200).all()
        rows=[]
        for link in links:
            item=db.get(SocialListeningResult,link.result_id)
            if not item or not _result_in_scope(db,p,item): continue
            try: match=json.loads(link.matched_fields_json or '[]')
            except (ValueError,TypeError): match=[]
            rows.append({'id':str(item.id),'platform':item.platform,'text_content':item.text_content,'canonical_url':item.canonical_url,'author_name':item.author_name,'published_at':item.published_at,'review_state':item.review_state,'content_type':item.content_type,'thumbnail_url':_existing_thumbnail(item),'matched_fields':match})
        return {'evidence':rows,'total':len(rows),'limited_to':200,'paid_provider_called':False}
    if action=='campaignKeywordPreview':
        from .campaign_scheduler import keyword_screen
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if not isinstance(data,dict) or not isinstance(data.get('text'),str):
            raise ValueError('Enter text for the keyword preview')
        sample=data['text'].strip()
        if len(sample)>5000: raise ValueError('Keyword preview is limited to 5000 characters')
        result=keyword_screen(c,{'text_content':sample})
        return {'screening':result,'paid_provider_called':False,
                'notice':'Local matching preview only; provider-side OR retrieval has not been verified'}
    if action=='campaignCostPreview':
        from .socialcrawl import estimate_search_cost
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        values=_normalize(db,p,data)
        filters={'query':' '.join(json.loads(values['primary_keywords_json'])),
                 'exclude_terms':json.loads(values['excluded_keywords_json']),
                 'platforms':json.loads(values['platforms_json']),
                 'language':values['language'],
                 'date_from':values['date_from'],'date_to':values['date_to'],
                 'province':values['province'],'regency_city':values['regency_city']}
        estimate=estimate_search_cost(filters)
        return {'estimated_credits':estimate['estimated_credits'],
                'components':estimate['components'],
                'billing_warning':'Estimate only. Actual provider credits may vary.',
                'paid_run_enabled':False,'approval_required':True}
    if action=='listCampaigns':
        rows=db.query(MonitoringCampaign).order_by(MonitoringCampaign.created_at.desc(),MonitoringCampaign.id.desc()).all()
        visible=[r for r in rows if allowed(p,r)]
        return {'campaigns':[_view(db,r) for r in visible[:MAX_CAMPAIGNS_PER_LIST]],'total':len(visible),
                'automatic_paid_crawling_enabled':False}
    if action in ('campaignSchedulePreview','campaignHistory'):
        from .campaign_scheduler import campaign_schedule_preview, campaign_history
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if action=='campaignSchedulePreview':
            return {'schedule':campaign_schedule_preview(db,c)}
        return {'history':campaign_history(db,c)}
    if action=='getCampaign':
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        return {'campaign':_view(db,c)}
    if action=='createCampaign':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted to create campaigns')
        values=_normalize(db,p,data)
        c=MonitoringCampaign(**values,status='DRAFT',created_by=p['id'])
        db.add(c);db.commit();db.refresh(c)
        audit(db,p,'MonitoringCampaign',c.id,'CAMPAIGN_CREATED',{'name':{'new':c.name},'status':{'new':'DRAFT'}})
        return {'campaign':_view(db,c),'message':'Campaign saved in draft; scheduled paid crawling is not enabled'}
    if action=='updateCampaign':
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if not _editable(p,c): raise PermissionError('Only campaign owner or national administrator can edit')
        if c.status not in ('DRAFT','PAUSED'): raise ValueError('Campaign cannot be edited in its current state')
        values=_normalize(db,p,{**_view(db,c),**(data or {})})
        for k,v in values.items(): setattr(c,k,v)
        # PAUSED is a configuration state, not a scheduler activation.
        desired=(data or {}).get('status',c.status)
        if desired not in ('DRAFT','PAUSED'): raise ValueError('Scheduled campaign activation is not yet available')
        previous_status=c.status;c.status=desired;c.updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        audit(db,p,'MonitoringCampaign',c.id,'CAMPAIGN_UPDATED',{'status':{'old':previous_status,'new':c.status}})
        return {'campaign':_view(db,c)}
    raise ValueError('Unsupported campaign action')
