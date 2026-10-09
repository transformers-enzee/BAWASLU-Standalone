import hashlib, json, os, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx
from sqlalchemy.orm import Session
from .models import SocialListeningRule, SocialListeningRun, SocialListeningResult, SocialListeningProviderUsage, IssueCategory, WatchlistItem, User
from .access import has, audit, allowed
from .domain import source_identity, create_intelligence

SOCIALCRAWL_BASE_URL=os.getenv('SOCIALCRAWL_BASE_URL','https://www.socialcrawl.dev').rstrip('/')
SOCIALCRAWL_API_KEY=os.getenv('SOCIALCRAWL_API_KEY','')
SOCIAL_PLATFORMS=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin']
AVAILABLE_PLATFORMS=SOCIAL_PLATFORMS+['online_news']
DEFAULT_PLATFORMS=list(SOCIAL_PLATFORMS)
SUPPORTED_EVERYWHERE_SOURCES=set(SOCIAL_PLATFORMS + ['hackernews','polymarket','github','pinterest','perplexity','tavily','rumble','tiktok-hashtag','instagram-hashtag','youtube-hashtag'])
SEARCH_EVERYWHERE_ESTIMATED_CREDITS=20
GOOGLE_NEWS_ESTIMATED_CREDITS=1

ALLOWED_FILTERS={
 'query','exact_phrase','include_terms','exclude_terms','hashtags','accounts','watchlist_ids','issue_category','topics','locations',
 'province','regency_city','date_from','date_to','lookback_days','language','platforms','content_types','minimum_relevance',
 'minimum_engagement','minimum_followers','verified_only','include_sources','exclude_sources','include_comments','sort','limit'
}

def _json(v): return json.dumps(v,ensure_ascii=False)
def _now(): return datetime.now(timezone.utc).isoformat()

def _normalize_filters(filters):
    f={k:v for k,v in (filters or {}).items() if k in ALLOWED_FILTERS and v not in (None,'',[],{})}
    if 'platforms' not in f: f['platforms']=DEFAULT_PLATFORMS
    if 'limit' not in f: f['limit']=50
    f['limit']=max(1,min(int(f['limit']),200))
    return f

def estimate_search_cost(filters):
    f=_normalize_filters(filters)
    selected=f.get('platforms') or DEFAULT_PLATFORMS
    social_sources=[x for x in selected if x!='online_news']
    wants_news='online_news' in selected
    components=[]
    total=0
    if social_sources:
        total+=SEARCH_EVERYWHERE_ESTIMATED_CREDITS
        components.append({'endpoint':'/v1/search/everywhere','credits':SEARCH_EVERYWHERE_ESTIMATED_CREDITS,'label':'Universal social search'})
    if wants_news:
        total+=GOOGLE_NEWS_ESTIMATED_CREDITS
        components.append({'endpoint':'/v1/google_news/search','credits':GOOGLE_NEWS_ESTIMATED_CREDITS,'label':'Online News'})
    return {'estimated_credits':total,'components':components,'result_limit':f.get('limit',50),'result_limit_affects_cost':False,'filters':f}

def _filter_fingerprint(filters):
    return hashlib.sha256(json.dumps(_normalize_filters(filters),sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def search_preflight(db:Session,p,filters):
    if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
    estimate=estimate_search_cost(filters)
    fingerprint=_filter_fingerprint(estimate['filters'])
    cutoff=datetime.utcnow()-timedelta(minutes=10)
    recent=db.query(SocialListeningRun).filter(SocialListeningRun.status=='COMPLETED',SocialListeningRun.executed_at>=cutoff).order_by(SocialListeningRun.executed_at.desc()).limit(50).all()
    duplicate=None
    for run in recent:
        try:
            if _filter_fingerprint(json.loads(run.query_json or '{}'))==fingerprint:
                age=max(0,int((datetime.utcnow()-run.executed_at).total_seconds()))
                duplicate={'run_id':str(run.id),'executed_at':run.executed_at.isoformat(),'seconds_ago':age,'credits_used':run.credits_used,'result_count':run.result_count,'cached':run.cached,'executed_by':run.executed_by}
                break
        except Exception:
            continue
    return {**estimate,'duplicate_recent':duplicate,'confirmation_required':estimate['estimated_credits']>0}

def usage_summary(db:Session,p):
    if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
    rows=db.query(SocialListeningProviderUsage).order_by(SocialListeningProviderUsage.created_at.desc()).limit(100).all()
    cutoff=datetime.utcnow()-timedelta(hours=24)
    recent=[x for x in rows if x.created_at>=cutoff]
    user_ids={str(x.user_id) for x in rows if x.user_id}
    names={}
    for uid in user_ids:
        try:
            user=db.get(User,int(uid))
            if user: names[uid]=user.full_name or user.email
        except Exception:
            pass
    items=[{'id':str(x.id),'provider':x.provider,'endpoint':x.endpoint,'request_id':x.provider_request_id,'credits_used':x.credits_used,'credits_remaining':x.credits_remaining,'cached':x.cached,'result_count':x.result_count,'user_id':x.user_id,'user_name':names.get(str(x.user_id),str(x.user_id or 'Unknown user')),'created_at':x.created_at.isoformat()} for x in rows]
    return {'usage':items,'summary':{'last_24h_credits':sum(x.credits_used for x in recent),'last_24h_calls':len(recent),'listed_credits':sum(x.credits_used for x in rows),'listed_calls':len(rows)}}

def _provider_source_name(name):
    n=str(name or '').strip().lower()
    if n in ('twitter','x','x/twitter'): return 'twitter-ai-search'
    if n=='facebook':
        raise ValueError('Facebook is not supported by SocialCrawl Universal Search Everywhere. Use a supported source or a dedicated Facebook endpoint.')
    if n not in SUPPORTED_EVERYWHERE_SOURCES:
        raise ValueError(f'Unsupported SocialCrawl source for Universal Search: {name}')
    return n

def _query_text(f):
    parts=[]
    if f.get('query'): parts.append(str(f['query']))
    if f.get('exact_phrase'): parts.append('"'+str(f['exact_phrase'])+'"')
    for x in f.get('include_terms',[]): parts.append(str(x))
    for x in f.get('exclude_terms',[]): parts.append('-'+str(x))
    for x in f.get('hashtags',[]): parts.append('#'+str(x).lstrip('#'))
    query=' '.join(parts).strip()
    if not query: raise ValueError('A SocialCrawl search query is required')
    return query

def _provider_params(filters):
    f=_normalize_filters(filters)
    params={'query':_query_text(f)}
    social_sources=[x for x in f.get('platforms',[]) if x!='online_news']
    if social_sources:
        params['sources']=','.join(_provider_source_name(x) for x in social_sources)
    if f.get('exclude_sources'):
        if params.get('sources'):
            raise ValueError('SocialCrawl sources and exclude cannot be used together')
        params['exclude']=','.join(_provider_source_name(x) for x in f['exclude_sources'])
    if f.get('date_from') or f.get('date_to'):
        if f.get('lookback_days'):
            raise ValueError('Choose either lookback days or an explicit date range, not both')
        if f.get('date_from'): params['from_date']=f['date_from']
        if f.get('date_to'): params['to_date']=f['date_to']
    elif f.get('lookback_days'):
        params['lookback_days']=f['lookback_days']
    if f.get('minimum_relevance') not in (None,''):
        params['relevance']='filter'
        params['relevance_threshold']=f['minimum_relevance']
    return params

def _news_params(filters):
    f=_normalize_filters(filters)
    params={'keyword':_query_text(f),'depth':min(max(int(f.get('limit') or 50),10),100)}
    if f.get('language'): params['language_code']=f['language']
    if f.get('date_from'): params['from']=f['date_from']
    if f.get('date_to'): params['to']=f['date_to']
    if not f.get('date_from') and not f.get('date_to') and f.get('lookback_days'):
        days=int(f['lookback_days'])
        params['time_range']='day' if days<=1 else 'week' if days<=7 else 'month' if days<=31 else 'year'
    return params

def _extract_items(envelope):
    data=envelope.get('data') or {}
    if isinstance(data,list): return data
    for k in ('items','results','posts','candidates'):
        if isinstance(data.get(k),list): return data[k]
    return []

def _value(item,*paths,default=''):
    for p in paths:
        cur=item
        ok=True
        for part in p.split('.'):
            if isinstance(cur,dict) and part in cur:
                cur=cur[part]
            elif isinstance(cur,list) and part.isdigit():
                idx=int(part)
                if 0 <= idx < len(cur): cur=cur[idx]
                else: ok=False; break
            else:
                ok=False; break
        if ok and cur not in (None,''): return cur
    return default

def _matches_local_filters(r, filters):
    f=_normalize_filters(filters)
    txt=(r.get('text_content') or '').lower()
    if f.get('language') and (r.get('language') or '').lower()!=str(f['language']).lower(): return False
    if f.get('accounts'):
        h=(r.get('observed_handle') or '').lower(); a=(r.get('author_name') or '').lower()
        wanted=[str(x).lower() for x in f['accounts']]
        if not any(x in h or x in a for x in wanted): return False
    if f.get('locations') and not any(str(x).lower() in txt for x in f['locations']): return False
    if f.get('topics') and not any(str(x).lower() in txt for x in f['topics']): return False
    if f.get('issue_category') and str(f['issue_category']).lower() not in txt: return False
    if f.get('content_types') and (r.get('content_type') or '').lower() not in [str(x).lower() for x in f['content_types']]: return False
    if f.get('minimum_relevance') not in (None,''):
        try:
            if float(r.get('relevance_score') or 0) < float(f['minimum_relevance']): return False
        except Exception: pass
    if f.get('minimum_engagement') not in (None,''):
        try:
            if float((r.get('engagement') or {}).get('engagement_rate') or 0) < float(f['minimum_engagement']): return False
        except Exception: pass
    return True

def _map_result(db,item):
    # SocialCrawl's normalized search rows are post-shaped:
    # post.content.text, post.author, post.engagement, post.published_at,
    # plus a sibling computed block. Keep legacy fallbacks for provider variations.
    url=str(_value(item,'post.url','url','canonical_url','permalink',default=''))
    author=str(_value(item,'post.author.display_name','post.author.username','source_items.0.author','author.display_name','author.name','author.username','username','owner.name','source',default=''))
    handle=str(_value(item,'post.author.username','source_items.0.author','author.username','author.handle','handle','username','owner.username',default=''))
    title=str(_value(item,'title','post.title',default=''))
    snippet=str(_value(item,'snippet',default=''))
    text=str(_value(item,'post.content.text','content.text','text','content','caption','description',default='')) or (' — '.join(x for x in [title,snippet] if x))
    platform=str(_value(item,'platform','source','network',default=''))
    rid=str(_value(item,'post.id','id','post_id','video_id','shortcode',default=''))
    language=str(_value(item,'computed.language','post.computed.language','source_items.0.metadata.language','source_items.0.language','language','metadata.language',default=''))
    relevance=_value(item,'computed.relevance.p','computed.relevance.score','relevance_score','relevance.score','score',default='')
    published=_value(item,'post.published_at','source_items.0.published_at','source_items.0.date','published_at','post.datetime','datetime','created_at','timestamp','date',default='')
    identity,observed=source_identity(db,{'source_url':url})
    if handle and not observed: observed=handle
    engagement={
      'views':_value(item,'post.engagement.views','source_items.0.engagement.views','engagement.views','metrics.views','views','view_count',default=None),
      'likes':_value(item,'post.engagement.likes','source_items.0.engagement.likes','engagement.likes','metrics.likes','likes','like_count',default=None),
      'comments':_value(item,'post.engagement.comments','source_items.0.engagement.comments','engagement.comments','metrics.comments','comments','comment_count',default=None),
      'shares':_value(item,'post.engagement.shares','source_items.0.engagement.shares','engagement.shares','metrics.shares','shares','share_count',default=None),
      'saves':_value(item,'post.engagement.saves','source_items.0.engagement.saves','engagement.saves','metrics.saves','saves',default=None),
      'engagement_rate':_value(item,'computed.engagement_rate','post.computed.engagement_rate','source_items.0.engagement.engagement_rate','engagement.engagement_rate','engagement_rate',default=None),
      'estimated_reach':_value(item,'computed.estimated_reach','post.computed.estimated_reach','source_items.0.engagement.estimated_reach','estimated_reach',default=None),
    }
    fp=hashlib.sha256((platform+'|'+rid+'|'+url+'|'+text[:2000]).encode()).hexdigest()
    return {'provider_result_id':rid,'platform':platform,'content_type':str(_value(item,'post.content.type','content_type','type',default='')),
      'canonical_url':url,'author_name':author,'observed_handle':observed or handle,'published_at':str(published or ''),
      'text_content':text,'language':language,'relevance_score':str(relevance) if relevance not in (None,'') else '','engagement':engagement,'geography':{},'source_identity':identity,
      'watchlist_matches':[],'content_fingerprint':fp,'raw':item}

def filter_options(db:Session,p):
    regions=json.loads(Path(__file__).with_name('regions.json').read_text(encoding='utf-8'))
    categories=db.query(IssueCategory).filter(IssueCategory.active.is_(True)).order_by(IssueCategory.sort_order,IssueCategory.name).all()
    watchlists=[x for x in db.query(WatchlistItem).filter(WatchlistItem.status=='Active').order_by(WatchlistItem.name).all() if allowed(p,x)]
    return {
      'issue_categories':[{'id':str(x.id),'name':x.name} for x in categories],
      'provinces':regions.get('provinces',[]),
      'regencies':regions.get('regencies',[]),
      'watchlists':[{'id':str(x.id),'name':x.name,'type':x.type,'province':x.province,'regency_city':x.regency_city} for x in watchlists],
      'platforms':AVAILABLE_PLATFORMS,
      'content_types':['post','video','short','reel','comment','reply'],
      'languages':[{'value':'id','label':'Bahasa Indonesia'},{'value':'en','label':'English'}],
      'sort_options':[{'value':'relevance','label':'Relevance'},{'value':'newest','label':'Newest'},{'value':'engagement','label':'Engagement'}]
    }

def capabilities():
    return {'provider':'SOCIALCRAWL','configured':bool(SOCIALCRAWL_API_KEY),'base_url':SOCIALCRAWL_BASE_URL,'endpoint':'/v1/search/everywhere','auth':'x-api-key',
      'platforms':AVAILABLE_PLATFORMS,'default_platforms':DEFAULT_PLATFORMS,'filters':sorted(ALLOWED_FILTERS),'credit_estimates':{'search_everywhere':SEARCH_EVERYWHERE_ESTIMATED_CREDITS,'google_news':GOOGLE_NEWS_ESTIMATED_CREDITS}}

def provider_status():
    if not SOCIALCRAWL_API_KEY:
        return {'provider':'SOCIALCRAWL','configured':False,'connected':False,'balance':None,'message':'SOCIALCRAWL_API_KEY is not configured in Render'}
    headers={'x-api-key':SOCIALCRAWL_API_KEY,'Accept':'application/json'}
    try:
        with httpx.Client(timeout=20) as client:
            res=client.get(SOCIALCRAWL_BASE_URL+'/v1/credits/balance',headers=headers)
        try: env=res.json()
        except Exception: env={}
        if res.status_code>=400 or env.get('success') is False:
            detail=env.get('error') or env.get('message') or res.text or f'HTTP {res.status_code}'
            if isinstance(detail,dict): detail=detail.get('message') or detail.get('type') or json.dumps(detail)
            return {'provider':'SOCIALCRAWL','configured':True,'connected':False,'balance':None,'message':str(detail)}
        data=env.get('data') or {}
        return {'provider':'SOCIALCRAWL','configured':True,'connected':True,'balance':data.get('balance',env.get('credits_remaining')),'request_id':env.get('request_id'),'credits_used':env.get('credits_used',0),'message':'Connected'}
    except Exception as e:
        return {'provider':'SOCIALCRAWL','configured':True,'connected':False,'balance':None,'message':str(e)}

def execute_search(db:Session,p,filters,rule_id=None,provider_client=None,confirmed_cost=False):
    if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
    f=_normalize_filters(filters)
    estimate=estimate_search_cost(f)
    if provider_client is None and estimate['estimated_credits']>0 and not confirmed_cost:
        raise ValueError(f"COST_CONFIRMATION_REQUIRED: estimated maximum {estimate['estimated_credits']} SocialCrawl credits")
    run=SocialListeningRun(rule_id=rule_id,query_json=_json(f),executed_by=p['id'],status='RUNNING'); db.add(run); db.commit(); db.refresh(run)
    selected=f.get('platforms') or DEFAULT_PLATFORMS
    wants_news='online_news' in selected
    social_sources=[x for x in selected if x!='online_news']
    endpoint='/v1/search/everywhere + /v1/google_news/search' if social_sources and wants_news else '/v1/google_news/search' if wants_news else '/v1/search/everywhere'
    try:
        if provider_client:
            envelope=provider_client(f)
        else:
            if not SOCIALCRAWL_API_KEY: raise ValueError('SOCIALCRAWL_API_KEY is not configured in Render')
            headers={'x-api-key':SOCIALCRAWL_API_KEY,'Accept':'application/json'}
            envelopes=[]
            def call_provider(path,params):
                with httpx.Client(timeout=75) as client:
                    res=client.get(SOCIALCRAWL_BASE_URL+path,params=params,headers=headers)
                    try: env=res.json()
                    except Exception: env={}
                    if res.status_code >= 400:
                        detail=(env.get('error') or env.get('message') or res.text or f'HTTP {res.status_code}')
                        if isinstance(detail,dict): detail=detail.get('message') or detail.get('type') or json.dumps(detail)
                        raise ValueError(f'SocialCrawl request failed ({res.status_code}): {detail}')
                    if env.get('success') is False:
                        detail=env.get('error') or env.get('message') or 'SocialCrawl returned success=false'
                        if isinstance(detail,dict): detail=detail.get('message') or detail.get('type') or json.dumps(detail)
                        raise ValueError(f'SocialCrawl request failed: {detail}')
                    return env
            if social_sources:
                sf=dict(f); sf['platforms']=social_sources
                envelopes.append(call_provider('/v1/search/everywhere',_provider_params(sf)))
            if wants_news:
                news_env=call_provider('/v1/google_news/search',_news_params(f))
                news_items=_extract_items(news_env)
                for item in news_items:
                    if isinstance(item,dict): item['platform']='online_news'
                if isinstance(news_env.get('data'),dict):
                    news_env['data']['items']=news_items
                else:
                    news_env['data']={'items':news_items}
                envelopes.append(news_env)
            if not envelopes: raise ValueError('Select at least one platform or Online News')
            envelope={
              'success':True,
              'request_id':','.join(str(x.get('request_id') or '') for x in envelopes if x.get('request_id')),
              'credits_used':sum(int(x.get('credits_used') or 0) for x in envelopes),
              'credits_remaining':next((int(x.get('credits_remaining')) for x in reversed(envelopes) if x.get('credits_remaining') is not None),0),
              'cached':all(bool(x.get('cached')) for x in envelopes),
              'data':{'items':[item for x in envelopes for item in _extract_items(x)]}
            }
        items=_extract_items(envelope)
        mapped=[]
        for raw in items:
            if len(mapped) >= f['limit']: break
            m=_map_result(db,raw)
            if not _matches_local_filters(m,f): continue
            existing=db.query(SocialListeningResult).filter(SocialListeningResult.content_fingerprint==m['content_fingerprint']).first()
            if existing: continue
            row=SocialListeningResult(run_id=run.id,provider_result_id=m['provider_result_id'],platform=m['platform'],content_type=m['content_type'],canonical_url=m['canonical_url'],author_name=m['author_name'],observed_handle=m['observed_handle'],published_at=m['published_at'],text_content=m['text_content'],language=m['language'],relevance_score=m['relevance_score'],engagement_json=_json(m['engagement']),geography_json=_json(m['geography']),source_identity_json=_json(m['source_identity']),watchlist_matches_json='[]',review_state='DISCOVERED',raw_payload_json=_json(m['raw']),content_fingerprint=m['content_fingerprint']); db.add(row); db.flush(); mapped.append(serialize_result(row))
        run.provider_request_id=str(envelope.get('request_id') or ''); run.credits_used=int(envelope.get('credits_used') or 0); run.credits_remaining=int(envelope.get('credits_remaining') or 0); run.cached=bool(envelope.get('cached')); run.result_count=len(mapped); run.status='COMPLETED'
        db.add(SocialListeningProviderUsage(provider='SOCIALCRAWL',endpoint=endpoint,provider_request_id=run.provider_request_id,credits_used=run.credits_used,credits_remaining=run.credits_remaining,cached=run.cached,result_count=len(mapped),user_id=p['id'])); db.commit()
        audit(db,p,'SocialListeningRun',run.id,'SOCIAL_LISTENING_SEARCH_EXECUTED',{'filters':{'new':f},'results':{'new':len(mapped)}})
        return {'run':serialize_run(run),'results':mapped,'provider':capabilities()}
    except Exception as e:
        run.status='FAILED'; run.error_text=str(e); db.commit()
        if isinstance(e,(ValueError,PermissionError)): raise
        raise ValueError(f'SocialCrawl search failed: {e}')

def serialize_rule(x): return {'id':str(x.id),'name':x.name,'description':x.description,'provider':x.provider,'enabled':x.enabled,'filters':json.loads(x.filters_json or '{}'),'created_by':x.created_by,'created_at':x.created_at.isoformat(),'updated_at':x.updated_at.isoformat()}
def serialize_run(x): return {'id':str(x.id),'rule_id':str(x.rule_id) if x.rule_id else None,'provider':x.provider,'query':json.loads(x.query_json or '{}'),'provider_request_id':x.provider_request_id,'credits_used':x.credits_used,'credits_remaining':x.credits_remaining,'cached':x.cached,'result_count':x.result_count,'status':x.status,'error_text':x.error_text,'executed_by':x.executed_by,'executed_at':x.executed_at.isoformat()}
def serialize_result(x): return {'id':str(x.id),'run_id':str(x.run_id),'provider':x.provider,'provider_result_id':x.provider_result_id,'platform':x.platform,'content_type':x.content_type,'canonical_url':x.canonical_url,'author_name':x.author_name,'observed_handle':x.observed_handle,'published_at':x.published_at,'text_content':x.text_content,'language':x.language,'relevance_score':x.relevance_score,'engagement':json.loads(x.engagement_json or '{}'),'geography':json.loads(x.geography_json or '{}'),'source_identity':json.loads(x.source_identity_json or '{}'),'watchlist_matches':json.loads(x.watchlist_matches_json or '[]'),'review_state':x.review_state,'review_notes':x.review_notes,'promoted_intelligence_id':str(x.promoted_intelligence_id) if x.promoted_intelligence_id else None,'collected_at':x.collected_at.isoformat()}

def social_listening_action(db,p,action,data,id=None,provider_client=None):
    if action=='capabilities': return capabilities()
    if action=='providerStatus': return provider_status()
    if action=='filterOptions': return filter_options(db,p)
    if action=='preflight': return search_preflight(db,p,data.get('filters') or data)
    if action=='search': return execute_search(db,p,data.get('filters') or data,provider_client=provider_client,confirmed_cost=bool(data.get('confirm_cost')))
    if action=='rules': return {'rules':[serialize_rule(x) for x in db.query(SocialListeningRule).order_by(SocialListeningRule.updated_at.desc()).all()]}
    if action=='saveRule':
        if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
        rid=str(id or data.get('id') or '')
        rule=db.get(SocialListeningRule,int(rid)) if rid.isdigit() else None
        if not rule: rule=SocialListeningRule(name=str(data.get('name') or 'Untitled monitoring rule'),created_by=p['id']); db.add(rule)
        rule.name=str(data.get('name') or rule.name); rule.description=str(data.get('description') or ''); rule.enabled=bool(data.get('enabled',True)); rule.filters_json=_json(_normalize_filters(data.get('filters') or {})); rule.updated_at=datetime.utcnow(); db.commit(); db.refresh(rule); audit(db,p,'SocialListeningRule',rule.id,'SOCIAL_LISTENING_RULE_SAVED',{'name':{'new':rule.name}}); return {'rule':serialize_rule(rule)}
    if action=='runRule':
        rule=db.get(SocialListeningRule,int(id)) if str(id or '').isdigit() else None
        if not rule or not rule.enabled: raise ValueError('Monitoring rule unavailable')
        return execute_search(db,p,json.loads(rule.filters_json or '{}'),rule_id=rule.id,provider_client=provider_client,confirmed_cost=bool(data.get('confirm_cost')))
    if action=='queue':
        if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
        all_rows=db.query(SocialListeningResult).order_by(SocialListeningResult.collected_at.desc()).limit(500).all()
        counts={'ALL':len(all_rows)}
        for key in ('DISCOVERED','RELEVANT','MONITOR','NOT_RELEVANT','PROMOTED'):
            counts[key]=sum(1 for x in all_rows if x.review_state==key)
        state=str(data.get('state') or '')
        if state and state not in counts: raise ValueError('Invalid social review queue state')
        rows=[x for x in all_rows if not state or x.review_state==state]
        return {'results':[serialize_result(x) for x in rows],'counts':counts}
    if action=='usage':
        return usage_summary(db,p)
    row=db.get(SocialListeningResult,int(id)) if str(id or '').isdigit() else None
    if not row: raise ValueError('Social listening result not found')
    if action=='review':
        decision=str(data.get('decision') or '')
        if decision not in ('RELEVANT','MONITOR','NOT_RELEVANT'): raise ValueError('Invalid decision')
        row.review_state=decision; row.review_notes=str(data.get('notes') or ''); db.commit(); audit(db,p,'SocialListeningResult',row.id,'SOCIAL_LISTENING_RESULT_REVIEWED',{'review_state':{'new':decision}}); return {'result':serialize_result(row)}
    if action=='promote':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        if row.promoted_intelligence_id: return {'intelligence_id':str(row.promoted_intelligence_id),'already_promoted':True}
        if row.review_state not in ('RELEVANT','MONITOR'):
            raise ValueError('Human review is required before adding this result to Intelligence')
        item=create_intelligence(db,p,{'title':(row.text_content[:160] or 'Social listening result'),'original_content':row.text_content,'source_type':'SOCIAL_LISTENING','ingestion_method':'SOCIALCRAWL','observed_publisher_handle':row.observed_handle,'provider_source_metadata':{'provider':'SOCIALCRAWL','run_id':row.run_id,'provider_result_id':row.provider_result_id},'source_identity':json.loads(row.source_identity_json or '{}'),'source_url':row.canonical_url,'source_name':row.author_name,'platform':row.platform,'author':row.author_name,'publication_datetime':row.published_at,'collection_datetime':_now(),'evidence_state':'UNVERIFIED','review_status':'Pending Review'})
        row.promoted_intelligence_id=item.id; row.review_state='PROMOTED'; db.commit(); audit(db,p,'SocialListeningResult',row.id,'SOCIAL_LISTENING_RESULT_PROMOTED',{'intelligence_id':{'new':item.intelligence_id}}); return {'intelligence_id':str(item.id),'intelligence_code':item.intelligence_id}
    raise ValueError('Unknown social listening action')
