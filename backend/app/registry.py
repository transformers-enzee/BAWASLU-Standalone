import json
from datetime import datetime
from sqlalchemy.orm import Session
from .models import *
from .serializers import *
from .access import *
from .domain import clean

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
        w=WatchlistItem(name=clean(data.get('name'),255),type=clean(data.get('type'),100),description=clean(data.get('description'),5000),province=clean(data.get('province'),128),regency_city=clean(data.get('regency_city'),128),related_election=clean(data.get('related_election'),255),related_entity=clean(data.get('related_entity'),255),related_topics_json=json.dumps(data.get('related_topics') or []),priority=clean(data.get('priority') or 'Medium',64),status=clean(data.get('status') or 'Active',64),notes=clean(data.get('notes'),5000)); db.add(w); db.commit(); db.refresh(w); audit(db,p,'WatchlistItem',w.id,'CREATED',{'name':{'new':w.name}}); return {'item':watchlist(w)}
    if action=='addAccount':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        w=db.get(WatchlistItem,int(id)) if str(id or '').isdigit() else None
        if not w or not allowed(p,w): raise ValueError('Watchlist item unavailable')
        a=SourceAccount(watchlist_id=w.id,platform=clean(data.get('platform'),100),url=clean(data.get('url'),2000),handle=clean(data.get('handle'),255),province=w.province,regency_city=w.regency_city); db.add(a); db.commit(); db.refresh(a); audit(db,p,'WatchlistItem',w.id,'SOURCE_ACCOUNT_ADDED',{'url':{'new':a.url}}); return {'account':source_account(a)}
    if action=='addRelationship':
        if not has(p,'manage_watchlist'): raise PermissionError('Not permitted')
        a=db.get(WatchlistItem,int(id)) if str(id or '').isdigit() else None; to=str(data.get('to_id','')); b=db.get(WatchlistItem,int(to)) if to.isdigit() else None
        if not a or not b or not allowed(p,a) or not allowed(p,b): raise ValueError('Entity unavailable')
        r=EntityRelationship(from_id=a.id,to_id=b.id,relationship_type=clean(data.get('relationship_type'),128),province=a.province); db.add(r); db.commit(); db.refresh(r); audit(db,p,'WatchlistItem',a.id,'RELATIONSHIP_ADDED',{'to_id':{'new':str(b.id)},'relationship_type':{'new':r.relationship_type}}); return {'relationship':relationship(r)}
    if action=='addSource':
        if not has(p,'administration'): raise PermissionError('Not permitted')
        s=DataSource(name=clean(data.get('name'),255),source_type=clean(data.get('source_type'),100),description=clean(data.get('description'),5000),status=clean(data.get('status') or 'Active',64),province=clean(data.get('province'),128),regency_city=clean(data.get('regency_city'),128)); db.add(s); db.commit(); db.refresh(s); return {'source':{'id':str(s.id),'name':s.name,'source_type':s.source_type,'description':s.description,'status':s.status,'province':s.province,'regency_city':s.regency_city}}
    if action=='category':
        if p.get('role')!='National Administrator' or not has(p,'administration'): raise PermissionError('Not permitted')
        c=IssueCategory(name=clean(data.get('name'),255),active=bool(data.get('active',True)),sort_order=int(data.get('sort_order') or 0)); db.add(c); db.commit(); db.refresh(c); return {'category':{'id':str(c.id),'name':c.name,'active':c.active,'sort_order':c.sort_order}}
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
        ev=db.query(AuditEvent).filter(AuditEvent.subject_type=='User',AuditEvent.subject_id==str(id)).order_by(AuditEvent.id.desc()).limit(50).all(); return {'events':[audit_event(x) for x in ev]}
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
        g.access_role=role; g.geographic_scope=scope; g.province=province; g.regency_city=city; g.permissions_json=json.dumps(perms); g.status=status; g.updated_at=datetime.utcnow(); db.commit(); audit(db,p,'User',u.id,'USER_ACCESS_UPDATED',{'assignment':{'previous':previous,'new':{'access_role':role,'geographic_scope':scope,'province':province,'regency_city':city,'permissions':perms,'status':status}}}); return {'ok':True,'user':{'id':str(u.id),'full_name':u.full_name,'email':u.email,'access_role':role,'province':province,'regency_city':city,'geographic_scope':scope,'permissions':perms,'status':status,'updated_date':g.updated_at.isoformat(),'platform_admin':u.platform_admin}}
    raise ValueError('Unknown action')
