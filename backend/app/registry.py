import json
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from sqlalchemy.orm import Session
from .models import *
from .serializers import *
from .access import *
from .domain import clean

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
    if action=='list':
        items=[x for x in db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all() if allowed(p,x)]
        ids={x.id for x in items}
        accounts=[x for x in db.query(SourceAccount).all() if x.watchlist_id in ids]
        rels=[x for x in db.query(EntityRelationship).all() if x.from_id in ids and x.to_id in ids]
        sources=[x for x in db.query(DataSource).all() if allowed(p,x)]
        cats=db.query(IssueCategory).order_by(IssueCategory.sort_order,IssueCategory.name).all()
        return {'items':[watchlist(x) for x in items],'accounts':[source_account(x) for x in accounts],'relationships':[relationship(x) for x in rels],'sources':[{'id':str(x.id),'name':x.name,'source_type':x.source_type,'description':x.description,'status':x.status,'province':x.province,'regency_city':x.regency_city} for x in sources],'categories':[{'id':str(x.id),'name':x.name,'active':x.active,'sort_order':x.sort_order} for x in cats]}

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
        if _account_duplicate(db,w.id,url,platform,handle): raise ValueError('This public account / URL is already registered for this watchlist item')
        a=SourceAccount(watchlist_id=w.id,platform=platform,url=url,handle=handle,province=w.province,regency_city=w.regency_city)
        db.add(a); db.commit(); db.refresh(a)
        audit(db,p,'WatchlistItem',w.id,'SOURCE_ACCOUNT_ADDED',{'account_id':{'new':str(a.id)},'url':{'new':a.url}})
        return {'account':source_account(a)}

    if action=='updateAccount':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        a=db.get(SourceAccount,int(id)) if str(id or '').isdigit() else None
        if not a: raise ValueError('Public account unavailable')
        w=_require_watchlist(db,p,a.watchlist_id)
        url=_normalize_url(data.get('url',a.url)); platform=clean(data.get('platform',a.platform) or 'Web',100); handle=_normalize_handle(data.get('handle',a.handle))
        if _account_duplicate(db,w.id,url,platform,handle,a.id): raise ValueError('This public account / URL is already registered for this watchlist item')
        previous=source_account(a)
        a.url=url; a.platform=platform; a.handle=handle; a.province=w.province; a.regency_city=w.regency_city
        db.commit(); db.refresh(a)
        audit(db,p,'WatchlistItem',w.id,'SOURCE_ACCOUNT_UPDATED',{'account_id':str(a.id),'previous':previous,'new':source_account(a)})
        return {'account':source_account(a)}

    if action=='removeAccount':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        a=db.get(SourceAccount,int(id)) if str(id or '').isdigit() else None
        if not a: raise ValueError('Public account unavailable')
        w=_require_watchlist(db,p,a.watchlist_id); previous=source_account(a)
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
        s=DataSource(name=clean(data.get('name'),255),source_type=clean(data.get('source_type'),100),description=clean(data.get('description'),5000),status=clean(data.get('status') or 'Active',64),province=clean(data.get('province'),128),regency_city=clean(data.get('regency_city'),128))
        db.add(s); db.commit(); db.refresh(s); return {'source':{'id':str(s.id),'name':s.name,'source_type':s.source_type,'description':s.description,'status':s.status,'province':s.province,'regency_city':s.regency_city}}

    if action=='category':
        if p.get('role')!='National Administrator' or not has(p,'administration'): raise PermissionError('Not permitted')
        c=IssueCategory(name=clean(data.get('name'),255),active=bool(data.get('active',True)),sort_order=int(data.get('sort_order') or 0)); db.add(c); db.commit(); db.refresh(c)
        return {'category':{'id':str(c.id),'name':c.name,'active':c.active,'sort_order':c.sort_order}}

    if action=='updateCategory':
        if p.get('role')!='National Administrator' or not has(p,'administration'): raise PermissionError('Not permitted')
        c=db.get(IssueCategory,int(id)) if str(id or '').isdigit() else None
        if not c: raise ValueError('Category not found')
        if 'name' in data: c.name=clean(data['name'],255)
        if 'active' in data: c.active=bool(data['active'])
        if 'sort_order' in data: c.sort_order=int(data['sort_order'] or 0)
        db.commit(); return {'ok':True}

    if action=='users':
        if not (has(p,'manage_users') and has(p,'administration')): raise PermissionError('Not permitted')
        rows=[]
        for u in db.query(User).order_by(User.created_at.desc()).all():
            up=profile(db,u)
            if p['geographic_scope']!='Nationwide' and not (up['province']==p['province'] and up['role'] not in NATIONAL): continue
            rows.append({'id':str(u.id),'full_name':u.full_name,'email':u.email,'access_role':up['role'],'province':up['province'],'regency_city':up['regency_city'],'geographic_scope':up['geographic_scope'],'permissions':up['permissions'],'status':up['status'],'updated_date':'','platform_admin':u.platform_admin})
        return {'users':rows,'administrator_role':p['role'],'administrator_province':p['province'],'roles':ROLE_DEFINITIONS,'permission_labels':PERMISSION_LABELS}

    if action=='accessHistory':
        if not (has(p,'manage_users') and has(p,'administration')): raise PermissionError('Not permitted')
        ev=db.query(AuditEvent).filter(AuditEvent.subject_type=='User',AuditEvent.subject_id==str(id)).order_by(AuditEvent.id.desc()).limit(50).all()
        return {'events':[audit_event(x) for x in ev]}

    if action=='setUser':
        if not (has(p,'manage_users') and has(p,'administration')): raise PermissionError('Not permitted')
        u=db.get(User,int(id)) if str(id or '').isdigit() else None
        if not u: raise ValueError('Not found')
        role=clean(data.get('access_role'),100)
        if role not in ROLE_DEFINITIONS: raise ValueError('Invalid role')
        scope=data.get('geographic_scope') or ROLE_DEFINITIONS[role]['scope']
        if scope=='Selectable': scope='Province'
        if scope not in ('Nationwide','Province','Regency/City'): raise ValueError('Choose a geographic scope')
        province='' if scope=='Nationwide' else clean(data.get('province'),128); city='' if scope!='Regency/City' else clean(data.get('regency_city'),128)
        if scope!='Nationwide' and not province: raise ValueError('Province required')
        if scope=='Regency/City' and not city: raise ValueError('Regency / City required')
        perms=data.get('permissions') or default_permissions(role)
        status=data.get('status') if data.get('status') in ('Active','Inactive') else 'Active'
        g=db.query(AccessGrant).filter(AccessGrant.user_id==u.id).one_or_none()
        if not g: g=AccessGrant(user_id=u.id); db.add(g)
        previous={'access_role':g.access_role,'geographic_scope':g.geographic_scope,'province':g.province,'regency_city':g.regency_city,'status':g.status}
        g.access_role=role; g.geographic_scope=scope; g.province=province; g.regency_city=city; g.permissions_json=json.dumps(perms); g.status=status; g.updated_at=datetime.utcnow(); db.commit()
        audit(db,p,'User',u.id,'USER_ACCESS_UPDATED',{'assignment':{'previous':previous,'new':{'access_role':role,'geographic_scope':scope,'province':province,'regency_city':city,'permissions':perms,'status':status}}})
        return {'ok':True,'user':{'id':str(u.id),'full_name':u.full_name,'email':u.email,'access_role':role,'province':province,'regency_city':city,'geographic_scope':scope,'permissions':perms,'status':status,'updated_date':g.updated_at.isoformat(),'platform_admin':u.platform_admin}}
    raise ValueError('Unknown action')
