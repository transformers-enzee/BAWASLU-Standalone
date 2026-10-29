import json
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from sqlalchemy.orm import Session
from .models import *
from .serializers import *
from .access import *
from .domain import clean

def _category_phrases(db, category_id):
    return [{'id':str(x.id),'phrase':x.phrase,'active':x.active} for x in db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.category_id==category_id).order_by(IssueCategoryPhrase.id).all()]

def _validated_category_phrases(raw):
    if not isinstance(raw,list): raise ValueError('Category phrases must be a list')
    if len(raw)>40: raise ValueError('Maximum 40 phrases per category')
    phrases={}
    for item in raw:
        phrase=clean(item,160).strip()
        normalized=' '.join(phrase.casefold().split())
        if not normalized: raise ValueError('Empty category phrase is not allowed')
        phrases[normalized]=phrase
    return phrases

def _sync_category_phrases(db,category_id,raw):
    incoming=_validated_category_phrases(raw)
    current={x.normalized_phrase:x for x in db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.category_id==category_id).all()}
    for norm,phrase in incoming.items():
        if norm in current:
            current[norm].active=True
        else:
            db.add(IssueCategoryPhrase(category_id=category_id,phrase=phrase,normalized_phrase=norm,active=True))
    for norm,row in current.items():
        if norm not in incoming: row.active=False


WATCHLIST_STATUSES={'Active','Under Review','Inactive'}
WATCHLIST_PRIORITIES={'Critical','High','Medium','Low'}

def _norm(value):
    return ' '.join(str(value or '').strip().lower().split())

def _require_watchlist(db,p,id):
    w=db.get(WatchlistItem,int(id)) if str(id or '').isdigit() else None
    if not w or not allowed(p,w): raise ValueError('Watchlist item unavailable')
    return w

def _normalize_url(value):
    raw=clean(value,2000)
    try: parsed=urlparse(raw)
    except Exception: parsed=None
    if not parsed or parsed.scheme.lower() not in ('http','https') or not parsed.hostname:
        raise ValueError('Public URL must be a valid http(s) URL')
    host=parsed.hostname.lower()
    port=f':{parsed.port}' if parsed.port else ''
    path=(parsed.path or '').rstrip('/')
    return urlunparse((parsed.scheme.lower(),host+port,path,'',parsed.query,''))

ACCOUNT_PLATFORM_HOSTS={
    'instagram':('instagram.com',),
    'tiktok':('tiktok.com',),
    'youtube':('youtube.com',),
    'facebook':('facebook.com','fb.com','fb.me'),
    'x':('x.com','twitter.com'),
    'twitter':('x.com','twitter.com'),
    'threads':('threads.net','threads.com'),
    'reddit':('reddit.com',),
    'linkedin':('linkedin.com',),
}

def _validate_account_domain(platform,url):
    allowed=ACCOUNT_PLATFORM_HOSTS.get(str(platform or '').strip().casefold())
    if not allowed:return
    hostname=(urlparse(url).hostname or '').lower()
    if not any(hostname==domain or hostname.endswith('.'+domain) for domain in allowed):
        raise ValueError('The public account URL must match the selected '+platform+' platform')

def _normalize_handle(value):
    raw=clean(value,255).replace(' ','')
    if not raw: return ''
    return raw if raw.startswith('@') else '@'+raw

def _duplicate_watchlist(db,data,exclude_id=None):
    name=_norm(data.get('name')); type_=_norm(data.get('type')); province=_norm(data.get('province')); city=_norm(data.get('regency_city'))
    if not name: return None
    for row in db.query(WatchlistItem).all():
        if exclude_id and row.id==exclude_id: continue
        if _norm(row.name)==name and _norm(row.type)==type_ and _norm(row.province)==province and _norm(row.regency_city)==city:
            return row
    return None

def _account_duplicate(db,watchlist_id,url,platform,handle,exclude_id=None):
    for row in db.query(SourceAccount).filter(SourceAccount.watchlist_id==watchlist_id).all():
        if exclude_id and row.id==exclude_id: continue
        if _norm(row.url)==_norm(url): return row
        if handle and _norm(row.platform)==_norm(platform) and _norm(row.handle)==_norm(handle): return row
    return None

def registry_action(db:Session,p,action,data,id=None):
    if p.get('status')!='Active': raise PermissionError('BAWASLU account access is inactive')
    if action=='myAccess': return {'access':p}
    # Protect every Watchlist, source and account listing action at the API boundary.
    if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
    if action=='list':
        items=[x for x in db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all() if allowed(p,x)]
        ids={x.id for x in items}
        accounts=[x for x in db.query(SourceAccount).all() if x.watchlist_id in ids]
        rels=[x for x in db.query(EntityRelationship).all() if x.from_id in ids and x.to_id in ids]
        sources=[x for x in db.query(DataSource).all() if allowed(p,x)]
        cats=db.query(IssueCategory).order_by(IssueCategory.sort_order,IssueCategory.name).all()
        return {'items':[watchlist(x) for x in items],'accounts':[source_account(x) for x in accounts],'relationships':[relationship(x) for x in rels],'sources':[{'id':str(x.id),'name':x.name,'source_type':x.source_type,'description':x.description,'status':x.status,'province':x.province,'regency_city':x.regency_city} for x in sources],'categories':[{'id':str(x.id),'name':x.name,'active':x.active,'sort_order':x.sort_order,'phrases':_category_phrases(db,x.id)} for x in cats]}

    if action=='watchlistSyncStatus':
        from .watchlist_auto import status_for
        watch=_require_watchlist(db,p,id)
        return status_for(db,watch.id)

    if action=='watchlistCapturedFeed':
        # Paginated, read-only evidence matching. Never call a crawl provider here.
        from datetime import date as _date
        from sqlalchemy import and_, or_, func
        from .socialcrawl import _result_in_scope
        from .campaigns import _captured_post_metrics
        w=_require_watchlist(db,p,id)
        accounts=db.query(SourceAccount).filter(SourceAccount.watchlist_id==w.id).order_by(SourceAccount.id).all()
        payload=data if isinstance(data,dict) else {}
        try:
            page=max(1,min(10000,int(payload.get('page') or 1)))
            page_size=max(1,min(50,int(payload.get('page_size') or 20)))
        except (ValueError,TypeError): raise ValueError('Invalid pagination')
        platform_filter=str(payload.get('platform') or '').strip().casefold()
        account_filter=str(payload.get('account_id') or '').strip()
        search=str(payload.get('search') or '').strip()[:120]
        def valid_day(key):
            value=str(payload.get(key) or '').strip()
            if not value:return ''
            try:return _date.fromisoformat(value).isoformat()
            except ValueError:raise ValueError(key+' must be YYYY-MM-DD')
        from_day=valid_day('date_from');to_day=valid_day('date_to')
        if from_day and to_day and from_day>to_day:raise ValueError('Date from must not exceed date to')
        def platform_key(value):
            value=str(value or '').casefold().strip()
            return 'x' if value=='twitter' else value
        def inferred_handle(account):
            supplied=str(account.handle or '').strip().lstrip('@').casefold()
            if supplied:return supplied
            parsed=urlparse(account.url or '')
            host=(parsed.hostname or '').lower()
            parts=[part for part in parsed.path.strip('/').split('/') if part]
            platform=platform_key(account.platform)
            allowed=ACCOUNT_PLATFORM_HOSTS.get(platform)
            if not allowed or not any(host==h or host.endswith('.'+h) for h in allowed):return ''
            if not parts:return ''
            first=parts[0]
            if platform in ('instagram','x','threads','tiktok'):
                if first.lower() in ('p','reel','reels','video','status','stories','explore','search'):return ''
                if platform=='tiktok' and not first.startswith('@'):return ''
                return first.lstrip('@').casefold()
            if platform=='youtube' and first.startswith('@'):return first[1:].casefold()
            if platform=='facebook' and first.lower() not in ('posts','groups','watch','reel','share','profile.php','story.php'):
                return first.casefold()
            if platform=='reddit' and len(parts)>=2 and first.lower() in ('user','u'):
                return parts[1].casefold()
            if platform=='linkedin' and len(parts)>=2 and first.lower() in ('in','company'):
                return parts[1].casefold()
            return ''
        specs={}
        for account in accounts:
            platform=platform_key(account.platform)
            if platform_filter and platform_filter!=platform:continue
            if account_filter and account_filter!=str(account.id):continue
            handle=inferred_handle(account)
            if platform and handle:
                specs.setdefault((platform,handle),account)
        base={'linked_accounts':len(accounts),'matchable_accounts':len(specs),
              'paid_provider_called':False,
              'status':'Stored captured evidence only. No automatic monitoring or provider requests.'}
        if not specs and not accounts:return {**base,'posts':[],'page':page,'page_size':page_size,'total':0}
        match_conditions=[]
        for (platform,handle),account in specs.items():
            platform_condition=func.lower(SocialListeningResult.platform).in_(
                ['x','twitter'] if platform=='x' else [platform])
            observed=func.lower(func.trim(SocialListeningResult.observed_handle))
            author=func.lower(func.trim(SocialListeningResult.author_name))
            matching=or_(observed.in_([handle,'@'+handle]),
                and_(or_(SocialListeningResult.observed_handle.is_(None),
                         func.trim(SocialListeningResult.observed_handle)==''),
                     author.in_([handle,'@'+handle])))
            match_conditions.append(and_(platform_condition,matching))
        explicit_account_ids=[a.id for a in accounts if (not platform_filter or
            a.platform.casefold()==platform_filter) and
            (not account_filter or str(a.id)==account_filter)]
        from .models import WatchlistAccountEvidence
        if explicit_account_ids:
            explicit=db.query(WatchlistAccountEvidence.result_id).filter(
                WatchlistAccountEvidence.account_id.in_(explicit_account_ids))
            match_conditions.append(SocialListeningResult.id.in_(explicit))
        # Never run an unfiltered query when account handles cannot be resolved.
        if not match_conditions:
            return {**base,'posts':[],'page':page,'page_size':page_size,'total':0}
        query=db.query(SocialListeningResult).filter(or_(*match_conditions))
        if from_day:query=query.filter(func.substr(SocialListeningResult.published_at,1,10)>=from_day)
        if to_day:query=query.filter(func.substr(SocialListeningResult.published_at,1,10)<=to_day)
        if search:
            escaped=search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            query=query.filter(SocialListeningResult.text_content.ilike('%'+escaped+'%',escape='\\'))
        query=query.order_by(SocialListeningResult.published_at.desc(),SocialListeningResult.id.desc())
        # Regional users must not learn the existence/count of out-of-scope records.
        if p.get('geographic_scope')=='Nationwide':
            total=query.order_by(None).count()
            rows=query.offset((page-1)*page_size).limit(page_size).all()
        else:
            total=0;rows=[];start=(page-1)*page_size
            for item in query.yield_per(200):
                if not _result_in_scope(db,p,item):continue
                if start<=total<start+page_size:rows.append(item)
                total+=1
        from .saved_assessment_views import saved_classifications_for_posts
        saved_views=saved_classifications_for_posts(db,p,rows)
        def serialize_post(item):
            platform=platform_key(item.platform)
            observed=str(item.observed_handle or '').strip().lstrip('@').casefold()
            author=str(item.author_name or '').strip().lstrip('@').casefold()
            matched=specs.get((platform,observed)) if observed else specs.get((platform,author))
            linked=db.query(SourceAccount).join(WatchlistAccountEvidence,
                WatchlistAccountEvidence.account_id==SourceAccount.id).filter(
                WatchlistAccountEvidence.result_id==item.id,
                SourceAccount.id.in_(explicit_account_ids)).first() if explicit_account_ids else None
            matched=linked or matched
            metrics=_captured_post_metrics(item.engagement_json)
            return {'id':str(item.id),'platform':item.platform,'account':matched.handle or '@'+inferred_handle(matched) if matched else '',
                'text':(item.text_content or '')[:5000],
                'published_at':item.published_at,'url':item.canonical_url,
                'author_name':item.author_name,'content_type':item.content_type,
                'match_method':'registered_account' if linked else 'observed_handle' if observed else 'author_name_unverified',
                'saved_assessments':saved_views.get(item.id,[]),
                **metrics}
        return {**base,'posts':[serialize_post(item) for item in rows],
                'page':page,'page_size':page_size,'total':total}

    if action=='createWatchlist':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        name=clean(data.get('name'),255); type_=clean(data.get('type'),100)
        if not name or not type_: raise ValueError('Name and type are required')
        if _duplicate_watchlist(db,data): raise ValueError('A watchlist item with the same name, type and geography already exists')
        status=clean(data.get('status') or 'Active',64); priority=clean(data.get('priority') or 'Medium',64)
        if status not in WATCHLIST_STATUSES: raise ValueError('Invalid monitoring status')
        if priority not in WATCHLIST_PRIORITIES: raise ValueError('Invalid monitoring priority')
        w=WatchlistItem(name=name,type=type_,description=clean(data.get('description'),5000),province=clean(data.get('province'),128),regency_city=clean(data.get('regency_city'),128),related_election=clean(data.get('related_election'),255),related_entity=clean(data.get('related_entity'),255),related_topics_json=json.dumps(data.get('related_topics') or []),priority=priority,status=status,notes=clean(data.get('notes'),5000))
        db.add(w); db.commit(); db.refresh(w)
        audit(db,p,'WatchlistItem',w.id,'CREATED',{'name':{'new':w.name},'status':{'new':w.status}})
        return {'item':watchlist(w)}

    if action=='updateWatchlist':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        w=_require_watchlist(db,p,id)
        candidate={'name':data.get('name',w.name),'type':data.get('type',w.type),'province':data.get('province',w.province),'regency_city':data.get('regency_city',w.regency_city)}
        if _duplicate_watchlist(db,candidate,w.id): raise ValueError('A watchlist item with the same name, type and geography already exists')
        previous=watchlist(w)
        if 'name' in data:
            w.name=clean(data.get('name'),255)
            if not w.name: raise ValueError('Name is required')
        if 'type' in data:
            w.type=clean(data.get('type'),100)
            if not w.type: raise ValueError('Type is required')
        if 'description' in data: w.description=clean(data.get('description'),5000)
        if 'province' in data: w.province=clean(data.get('province'),128)
        if 'regency_city' in data: w.regency_city=clean(data.get('regency_city'),128)
        if 'related_election' in data: w.related_election=clean(data.get('related_election'),255)
        if 'related_entity' in data: w.related_entity=clean(data.get('related_entity'),255)
        if 'related_topics' in data: w.related_topics_json=json.dumps(data.get('related_topics') or [])
        if 'priority' in data:
            priority=clean(data.get('priority'),64)
            if priority not in WATCHLIST_PRIORITIES: raise ValueError('Invalid monitoring priority')
            w.priority=priority
        if 'status' in data:
            status=clean(data.get('status'),64)
            if status not in WATCHLIST_STATUSES: raise ValueError('Invalid monitoring status')
            w.status=status
        if 'notes' in data: w.notes=clean(data.get('notes'),5000)
        w.updated_at=datetime.utcnow(); db.commit(); db.refresh(w)
        current=watchlist(w)
        audit(db,p,'WatchlistItem',w.id,'UPDATED',{'previous':previous,'new':current})
        return {'item':current}

    if action=='addAccount':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        w=_require_watchlist(db,p,id)
        url=_normalize_url(data.get('url')); platform=clean(data.get('platform') or 'Web',100); handle=_normalize_handle(data.get('handle'))
        _validate_account_domain(platform,url)
        if _account_duplicate(db,w.id,url,platform,handle): raise ValueError('This public account / URL is already registered for this watchlist item')
        a=SourceAccount(watchlist_id=w.id,platform=platform,url=url,handle=handle,province=w.province,regency_city=w.regency_city)
        db.add(a); db.commit(); db.refresh(a)
        from .watchlist_auto import mark_pending
        mark_pending(db,a.id)
        audit(db,p,'WatchlistItem',w.id,'SOURCE_ACCOUNT_ADDED',{'account_id':{'new':str(a.id)},'url':{'new':a.url}})
        return {'account':source_account(a)}

    if action=='updateAccount':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        a=db.get(SourceAccount,int(id)) if str(id or '').isdigit() else None
        if not a: raise ValueError('Public account unavailable')
        w=_require_watchlist(db,p,a.watchlist_id)
        url=_normalize_url(data.get('url',a.url)); platform=clean(data.get('platform',a.platform) or 'Web',100); handle=_normalize_handle(data.get('handle',a.handle))
        _validate_account_domain(platform,url)
        if _account_duplicate(db,w.id,url,platform,handle,a.id): raise ValueError('This public account / URL is already registered for this watchlist item')
        previous=source_account(a)
        a.url=url; a.platform=platform; a.handle=handle; a.province=w.province; a.regency_city=w.regency_city
        db.commit(); db.refresh(a)
        from .watchlist_auto import mark_pending
        mark_pending(db,a.id)
        audit(db,p,'WatchlistItem',w.id,'SOURCE_ACCOUNT_UPDATED',{'account_id':str(a.id),'previous':previous,'new':source_account(a)})
        return {'account':source_account(a)}

    if action=='removeAccount':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        a=db.get(SourceAccount,int(id)) if str(id or '').isdigit() else None
        if not a: raise ValueError('Public account unavailable')
        w=_require_watchlist(db,p,a.watchlist_id); previous=source_account(a)
        from .models import WatchlistAccountSync, WatchlistAccountEvidence
        db.query(WatchlistAccountEvidence).filter(
            WatchlistAccountEvidence.account_id==a.id).delete(synchronize_session=False)
        db.query(WatchlistAccountSync).filter(
            WatchlistAccountSync.account_id==a.id).delete(synchronize_session=False)
        db.delete(a); db.commit()
        audit(db,p,'WatchlistItem',w.id,'SOURCE_ACCOUNT_REMOVED',{'account':previous})
        return {'ok':True}

    if action=='addRelationship':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        a=_require_watchlist(db,p,id)
        to=str(data.get('to_id','')); b=db.get(WatchlistItem,int(to)) if to.isdigit() else None
        if not b or not allowed(p,b): raise ValueError('Entity unavailable')
        if a.id==b.id: raise ValueError('A watchlist item cannot be related to itself')
        kind=clean(data.get('relationship_type'),128)
        if not kind: raise ValueError('Relationship type is required')
        for row in db.query(EntityRelationship).filter(EntityRelationship.from_id==a.id,EntityRelationship.to_id==b.id).all():
            if _norm(row.relationship_type)==_norm(kind): raise ValueError('This relationship already exists')
        r=EntityRelationship(from_id=a.id,to_id=b.id,relationship_type=kind,province=a.province)
        db.add(r); db.commit(); db.refresh(r)
        audit(db,p,'WatchlistItem',a.id,'RELATIONSHIP_ADDED',{'relationship_id':{'new':str(r.id)},'to_id':{'new':str(b.id)},'relationship_type':{'new':r.relationship_type}})
        return {'relationship':relationship(r)}

    if action=='removeRelationship':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        r=db.get(EntityRelationship,int(id)) if str(id or '').isdigit() else None
        if not r: raise ValueError('Relationship unavailable')
        a=_require_watchlist(db,p,r.from_id); b=_require_watchlist(db,p,r.to_id); previous=relationship(r)
        db.delete(r); db.commit()
        audit(db,p,'WatchlistItem',a.id,'RELATIONSHIP_REMOVED',{'relationship':previous,'to_name':b.name})
        return {'ok':True}

    if action=='addSource':
        if not has(p,'administration'): raise PermissionError('Not permitted')
        name=clean(data.get('name'),255); source_type=clean(data.get('source_type'),100)
        if not name: raise ValueError('Source name is required')
        if not source_type: raise ValueError('Source type is required')
        if source_type not in {'MANUAL_LINK','MANUAL_ENTRY','FILE_UPLOAD','INTERNAL_BAWASLU','OFFICIAL_SOURCE'}: raise ValueError('Invalid source type')
        status=clean(data.get('status') or 'Active',64)
        if status not in {'Active','Inactive'}: raise ValueError('Invalid source status')
        s=DataSource(name=name,source_type=source_type,description=clean(data.get('description'),5000),status=status,province=clean(data.get('province'),128),regency_city=clean(data.get('regency_city'),128))
        db.add(s); db.commit(); db.refresh(s)
        audit(db,p,'DataSource',s.id,'CREATED',{'name':{'new':s.name},'source_type':{'new':s.source_type},'status':{'new':s.status}})
        return {'source':{'id':str(s.id),'name':s.name,'source_type':s.source_type,'description':s.description,'status':s.status,'province':s.province,'regency_city':s.regency_city}}

    if action=='updateSource':
        if not has(p,'administration'): raise PermissionError('Not permitted')
        s=db.get(DataSource,int(id)) if str(id or '').isdigit() else None
        if not s or not allowed(p,s): raise ValueError('Data source unavailable')
        previous={'name':s.name,'source_type':s.source_type,'description':s.description,'status':s.status,'province':s.province,'regency_city':s.regency_city}
        if 'name' in data:
            s.name=clean(data.get('name'),255)
            if not s.name: raise ValueError('Source name is required')
        if 'source_type' in data:
            source_type=clean(data.get('source_type'),100)
            if source_type not in {'MANUAL_LINK','MANUAL_ENTRY','FILE_UPLOAD','INTERNAL_BAWASLU','OFFICIAL_SOURCE'}: raise ValueError('Invalid source type')
            s.source_type=source_type
        if 'description' in data: s.description=clean(data.get('description'),5000)
        if 'status' in data:
            status=clean(data.get('status'),64)
            if status not in {'Active','Inactive'}: raise ValueError('Invalid source status')
            s.status=status
        if 'province' in data: s.province=clean(data.get('province'),128)
        if 'regency_city' in data: s.regency_city=clean(data.get('regency_city'),128)
        db.commit(); db.refresh(s)
        current={'name':s.name,'source_type':s.source_type,'description':s.description,'status':s.status,'province':s.province,'regency_city':s.regency_city}
        audit(db,p,'DataSource',s.id,'UPDATED',{'previous':previous,'new':current})
        return {'source':{'id':str(s.id),'name':s.name,'source_type':s.source_type,'description':s.description,'status':s.status,'province':s.province,'regency_city':s.regency_city}}

    if action=='category':
        if p.get('role')!='National Administrator' or not has(p,'administration'): raise PermissionError('Not permitted')
        c=IssueCategory(name=clean(data.get('name'),255),active=bool(data.get('active',True)),sort_order=int(data.get('sort_order') or 0)); db.add(c); db.flush()
        if 'phrases' in data: _sync_category_phrases(db,c.id,data['phrases'])
        db.commit(); db.refresh(c)
        audit(db,p,'IssueCategory',c.id,'CREATED',{'name':{'new':c.name}})
        return {'category':{'id':str(c.id),'name':c.name,'active':c.active,'sort_order':c.sort_order,'phrases':_category_phrases(db,c.id)}}

    if action=='updateCategory':
        if p.get('role')!='National Administrator' or not has(p,'administration'): raise PermissionError('Not permitted')
        c=db.get(IssueCategory,int(id)) if str(id or '').isdigit() else None
        if not c: raise ValueError('Category not found')
        if 'name' in data: c.name=clean(data['name'],255)
        if 'active' in data: c.active=bool(data['active'])
        if 'sort_order' in data: c.sort_order=int(data['sort_order'] or 0)
        if 'phrases' in data: _sync_category_phrases(db,c.id,data['phrases'])
        db.commit()
        audit(db,p,'IssueCategory',c.id,'UPDATED',{'category':{'new':c.name},'phrases':{'new':_category_phrases(db,c.id)}})
        return {'ok':True}

    if action=='users':
        if not (has(p,'manage_users') and has(p,'administration')): raise PermissionError('Not permitted')
        rows=[]
        for u in db.query(User).order_by(User.created_at.desc()).all():
            up=profile(db,u)
            if p['geographic_scope']!='Nationwide' and not (up['province']==p['province'] and up['role'] not in NATIONAL): continue
            grant=db.query(AccessGrant).filter(AccessGrant.user_id==u.id).one_or_none()
            rows.append({'id':str(u.id),'full_name':u.full_name,'email':u.email,'access_role':up['role'],'province':up['province'],'regency_city':up['regency_city'],'geographic_scope':up['geographic_scope'],'permissions':up['permissions'],'status':up['status'],'updated_date':grant.updated_at.isoformat() if grant and grant.updated_at else '','platform_admin':u.platform_admin})
        return {'users':rows,'administrator_role':p['role'],'administrator_province':p['province'],'roles':ROLE_DEFINITIONS,'permission_labels':PERMISSION_LABELS}

    if action=='accessHistory':
        if not (has(p,'manage_users') and has(p,'administration')): raise PermissionError('Not permitted')
        ev=db.query(AuditEvent).filter(AuditEvent.subject_type=='User',AuditEvent.subject_id==str(id)).order_by(AuditEvent.id.desc()).limit(50).all()
        return {'events':[audit_event(x) for x in ev]}

    if action=='setUser':
        if not (has(p,'manage_users') and has(p,'administration')): raise PermissionError('Not permitted')
        u=db.get(User,int(id)) if str(id or '').isdigit() else None
        if not u: raise ValueError('Not found')
        if str(u.id)==str(p.get('id')): raise PermissionError('Administrators cannot change their own access assignment')
        target_profile=profile(db,u)
        if p.get('role')=='Provincial Administrator' and (target_profile.get('province')!=p.get('province') or target_profile.get('role') in NATIONAL):
            raise PermissionError('Target user is outside the administrator scope')
        role=clean(data.get('access_role'),100)
        if role not in ROLE_DEFINITIONS: raise ValueError('Invalid role')
        if p.get('role')=='Provincial Administrator' and role in NATIONAL: raise PermissionError('Provincial administrators cannot assign national roles')
        scope=data.get('geographic_scope') or ROLE_DEFINITIONS[role]['scope']
        if scope=='Selectable': scope='Province'
        if scope not in ('Nationwide','Province','Regency/City'): raise ValueError('Choose a geographic scope')
        if p.get('role')=='Provincial Administrator' and scope=='Nationwide': raise PermissionError('Provincial administrators cannot assign nationwide access')
        province='' if scope=='Nationwide' else clean(data.get('province'),128); city='' if scope!='Regency/City' else clean(data.get('regency_city'),128)
        if p.get('role')=='Provincial Administrator':
            if province and province!=p.get('province'): raise PermissionError('Access may only be assigned within the administrator province')
            province=p.get('province') or ''
        if scope!='Nationwide' and not province: raise ValueError('Province required')
        if scope=='Regency/City' and not city: raise ValueError('Regency / City required')
        # Omitted permissions use the selected role's defaults. An explicitly
        # empty object means revoke all permissions; never silently re-grant.
        if 'permissions' in data:
            raw_permissions=data['permissions']
            if not isinstance(raw_permissions,dict):
                raise ValueError('Permissions must be an object')
        else:
            raw_permissions=default_permissions(role)
        perms={key:raw_permissions.get(key) is True for key in PERMISSION_LABELS}
        for key,enabled in perms.items():
            if enabled and not p.get('permissions',{}).get(key,False):
                raise PermissionError('Cannot delegate a permission the administrator does not hold')
        status=data.get('status') if data.get('status') in ('Active','Inactive') else 'Active'
        g=db.query(AccessGrant).filter(AccessGrant.user_id==u.id).one_or_none()
        if not g: g=AccessGrant(user_id=u.id); db.add(g)
        previous={'access_role':g.access_role,'geographic_scope':g.geographic_scope,'province':g.province,'regency_city':g.regency_city,'status':g.status}
        g.access_role=role; g.geographic_scope=scope; g.province=province; g.regency_city=city; g.permissions_json=json.dumps(perms); g.status=status; g.updated_at=datetime.utcnow(); db.commit()
        audit(db,p,'User',u.id,'USER_ACCESS_UPDATED',{'assignment':{'previous':previous,'new':{'access_role':role,'geographic_scope':scope,'province':province,'regency_city':city,'permissions':perms,'status':status}}})
        return {'ok':True,'user':{'id':str(u.id),'full_name':u.full_name,'email':u.email,'access_role':role,'province':province,'regency_city':city,'geographic_scope':scope,'permissions':perms,'status':status,'updated_date':g.updated_at.isoformat(),'platform_admin':u.platform_admin}}
    raise ValueError('Unknown action')
