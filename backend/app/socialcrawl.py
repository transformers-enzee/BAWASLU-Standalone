import hashlib, json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
import httpx
from sqlalchemy.orm import Session
from .models import SocialListeningRule, SocialListeningRun, SocialListeningResult, SocialListeningProviderUsage, IssueCategory, WatchlistItem
from .access import has, audit, allowed
from .domain import source_identity, create_intelligence

SOCIALCRAWL_BASE_URL=os.getenv('SOCIALCRAWL_BASE_URL','https://www.socialcrawl.dev').rstrip('/')
SOCIALCRAWL_API_KEY=os.getenv('SOCIALCRAWL_API_KEY','')
DEFAULT_PLATFORMS=['tiktok','instagram','youtube','twitter-ai-search','threads','reddit','linkedin']
SUPPORTED_EVERYWHERE_SOURCES=set(DEFAULT_PLATFORMS + ['hackernews','polymarket','github','pinterest','perplexity','tavily','rumble','tiktok-hashtag','instagram-hashtag','youtube-hashtag'])

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

def _provider_source_name(name):
    n=str(name or '').strip().lower()
    if n in ('twitter','x','x/twitter'): return 'twitter-ai-search'
    if n=='facebook':
        raise ValueError('Facebook is not supported by SocialCrawl Universal Search Everywhere. Use a supported source or a dedicated Facebook endpoint.')
    if n not in SUPPORTED_EVERYWHERE_SOURCES:
        raise ValueError(f'Unsupported SocialCrawl source for Universal Search: {name}')
    return n

def _provider_params(filters):
    f=_normalize_filters(filters)
    parts=[]
    if f.get('query'): parts.append(str(f['query']))
    if f.get('exact_phrase'): parts.append('"'+str(f['exact_phrase'])+'"')
    for x in f.get('include_terms',[]): parts.append(str(x))
    for x in f.get('exclude_terms',[]): parts.append('-'+str(x))
    for x in f.get('hashtags',[]): parts.append('#'+str(x).lstrip('#'))
    query=' '.join(parts).strip()
    if not query:
        raise ValueError('A SocialCrawl search query is required')
    params={'query':query}
    if f.get('platforms'):
        params['sources']=','.join(_provider_source_name(x) for x in f['platforms'])
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
            if isinstance(cur,dict) and part in cur: cur=cur[part]
            else: ok=False; break
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
    url=str(_value(item,'url','canonical_url','permalink','post.url',default=''))
    author=str(_value(item,'author.name','author.display_name','username','owner.name',default=''))
    handle=str(_value(item,'author.handle','handle','username','owner.username',default=''))
    text=str(_value(item,'text','content','caption','title','description',default=''))
    platform=str(_value(item,'platform','source','network',default=''))
    rid=str(_value(item,'id','post_id','video_id','shortcode',default=''))
    language=str(_value(item,'language','computed.language',default=''))
    relevance=_value(item,'computed.relevance.p','relevance_score','relevance.score','score',default='')
    identity,observed=source_identity(db,{'source_url':url})
    if handle and not observed: observed=handle
    engagement={
      'views':_value(item,'metrics.views','views','view_count',default=None),
      'likes':_value(item,'metrics.likes','likes','like_count',default=None),
      'comments':_value(item,'metrics.comments','comments','comment_count',default=None),
      'shares':_value(item,'metrics.shares','shares','share_count',default=None),
      'engagement_rate':_value(item,'engagement_rate','computed.engagement_rate',default=None),
      'estimated_reach':_value(item,'estimated_reach','computed.estimated_reach',default=None),
    }
    fp=hashlib.sha256((platform+'|'+rid+'|'+url+'|'+text[:2000]).encode()).hexdigest()
    return {'provider_result_id':rid,'platform':platform,'content_type':str(_value(item,'content_type','type',default='')),
      'canonical_url':url,'author_name':author,'observed_handle':observed or handle,'published_at':str(_value(item,'published_at','created_at','timestamp','date',default='')),
      'text_content':text,'language':language,'relevance_score':str(relevance),'engagement':engagement,'geography':{},'source_identity':identity,
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
      'platforms':DEFAULT_PLATFORMS,
      'content_types':['post','video','short','reel','comment','reply'],
      'languages':[{'value':'id','label':'Bahasa Indonesia'},{'value':'en','label':'English'}],
      'sort_options':[{'value':'relevance','label':'Relevance'},{'value':'newest','label':'Newest'},{'value':'engagement','label':'Engagement'}]
    }

def capabilities():
    return {'provider':'SOCIALCRAWL','configured':bool(SOCIALCRAWL_API_KEY),'base_url':SOCIALCRAWL_BASE_URL,'endpoint':'/v1/search/everywhere','auth':'x-api-key',
      'platforms':DEFAULT_PLATFORMS,'filters':sorted(ALLOWED_FILTERS)}

def execute_search(db:Session,p,filters,rule_id=None,provider_client=None):
    if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
    f=_normalize_filters(filters)
    run=SocialListeningRun(rule_id=rule_id,query_json=_json(f),executed_by=p['id'],status='RUNNING'); db.add(run); db.commit(); db.refresh(run)
    endpoint='/v1/search/everywhere'
    try:
        if provider_client:
            envelope=provider_client(f)
        else:
            if not SOCIALCRAWL_API_KEY: raise ValueError('SOCIALCRAWL_API_KEY is not configured in Render')
            headers={'x-api-key':SOCIALCRAWL_API_KEY,'Accept':'application/json'}
            with httpx.Client(timeout=75) as client:
                res=client.get(SOCIALCRAWL_BASE_URL+endpoint,params=_provider_params(f),headers=headers)
                try:
                    envelope=res.json()
                except Exception:
                    envelope={}
                if res.status_code >= 400:
                    detail=(envelope.get('error') or envelope.get('message') or res.text or f'HTTP {res.status_code}')
                    if isinstance(detail,dict): detail=detail.get('message') or detail.get('type') or json.dumps(detail)
                    raise ValueError(f'SocialCrawl request failed ({res.status_code}): {detail}')
                if envelope.get('success') is False:
                    detail=envelope.get('error') or envelope.get('message') or 'SocialCrawl returned success=false'
                    if isinstance(detail,dict): detail=detail.get('message') or detail.get('type') or json.dumps(detail)
                    raise ValueError(f'SocialCrawl request failed: {detail}')
        items=_extract_items(envelope)
        mapped=[]
        for raw in items:
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
    if action=='filterOptions': return filter_options(db,p)
    if action=='search': return execute_search(db,p,data.get('filters') or data,provider_client=provider_client)
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
        return execute_search(db,p,json.loads(rule.filters_json or '{}'),rule_id=rule.id,provider_client=provider_client)
    if action=='queue':
        rows=db.query(SocialListeningResult).order_by(SocialListeningResult.collected_at.desc()).limit(500).all()
        state=data.get('state')
        if state: rows=[x for x in rows if x.review_state==state]
        return {'results':[serialize_result(x) for x in rows]}
    row=db.get(SocialListeningResult,int(id)) if str(id or '').isdigit() else None
    if not row: raise ValueError('Social listening result not found')
    if action=='review':
        decision=str(data.get('decision') or '')
        if decision not in ('RELEVANT','MONITOR','NOT_RELEVANT'): raise ValueError('Invalid decision')
        row.review_state=decision; row.review_notes=str(data.get('notes') or ''); db.commit(); audit(db,p,'SocialListeningResult',row.id,'SOCIAL_LISTENING_RESULT_REVIEWED',{'review_state':{'new':decision}}); return {'result':serialize_result(row)}
    if action=='promote':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        if row.promoted_intelligence_id: return {'intelligence_id':str(row.promoted_intelligence_id),'already_promoted':True}
        item=create_intelligence(db,p,{'title':(row.text_content[:160] or 'Social listening result'),'original_content':row.text_content,'source_type':'SOCIAL_LISTENING','ingestion_method':'SOCIALCRAWL','observed_publisher_handle':row.observed_handle,'provider_source_metadata':{'provider':'SOCIALCRAWL','run_id':row.run_id,'provider_result_id':row.provider_result_id},'source_identity':json.loads(row.source_identity_json or '{}'),'source_url':row.canonical_url,'source_name':row.author_name,'platform':row.platform,'author':row.author_name,'publication_datetime':row.published_at,'collection_datetime':_now(),'evidence_state':'UNVERIFIED','review_status':'Pending Review'})
        row.promoted_intelligence_id=item.id; row.review_state='PROMOTED'; db.commit(); audit(db,p,'SocialListeningResult',row.id,'SOCIAL_LISTENING_RESULT_PROMOTED',{'intelligence_id':{'new':item.intelligence_id}}); return {'intelligence_id':str(item.id),'intelligence_code':item.intelligence_id}
    if action=='usage':
        rows=db.query(SocialListeningProviderUsage).order_by(SocialListeningProviderUsage.created_at.desc()).limit(100).all()
        return {'usage':[{'id':str(x.id),'provider':x.provider,'endpoint':x.endpoint,'request_id':x.provider_request_id,'credits_used':x.credits_used,'credits_remaining':x.credits_remaining,'cached':x.cached,'result_count':x.result_count,'user_id':x.user_id,'created_at':x.created_at.isoformat()} for x in rows]}
    raise ValueError('Unknown social listening action')
