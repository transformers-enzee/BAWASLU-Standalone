import json
from dataclasses import dataclass
from sqlalchemy.orm import Session
from .models import AccessGrant, User, AuditEvent

PERMISSION_LABELS={
 'view_intelligence':'View Intelligence','add_intelligence':'Add Intelligence','edit_intelligence':'Edit Intelligence',
 'review_ai_suggestions':'Review AI Suggestions','human_validation':'Human Validation','verify_evidence':'Verify Evidence',
 'manage_watchlist':'Manage Watchlist','upload_evidence':'Upload Supporting Evidence','manage_users':'Manage Users & Access','administration':'Administration'
}
VIEW=['view_intelligence']; ANALYST=VIEW+['add_intelligence','edit_intelligence','review_ai_suggestions','upload_evidence']; MANAGER=ANALYST+['human_validation','verify_evidence','manage_watchlist','manage_users','administration']
ROLE_DEFINITIONS={
 'National Administrator':{'scope':'Nationwide','permissions':list(PERMISSION_LABELS)},
 'National Leadership':{'scope':'Nationwide','permissions':VIEW},
 'National Analyst':{'scope':'Nationwide','permissions':ANALYST+['human_validation','verify_evidence','manage_watchlist']},
 'Provincial Administrator':{'scope':'Province','permissions':MANAGER},
 'Provincial Analyst':{'scope':'Province','permissions':ANALYST},
 'Regency/City Officer':{'scope':'Regency/City','permissions':ANALYST},
 'Regency/City Analyst':{'scope':'Regency/City','permissions':ANALYST},
 'Viewer':{'scope':'Selectable','permissions':VIEW},
}
NATIONAL={'National Administrator','National Leadership','National Analyst'}

def default_permissions(role):
    allowed=set(ROLE_DEFINITIONS.get(role,{}).get('permissions',[]))
    return {k:k in allowed for k in PERMISSION_LABELS}

def profile(db:Session,user:User):
    grant=db.query(AccessGrant).filter(AccessGrant.user_id==user.id).one_or_none()
    role=grant.access_role if grant else 'Viewer'
    perms=json.loads(grant.permissions_json or '{}') if grant else {}
    if not perms: perms=default_permissions(role)
    return {
      'id':str(user.id),'name':user.full_name or user.email,'email':user.email,'role':role,
      'province':grant.province if grant else '','regency_city':grant.regency_city if grant else '',
      'geographic_scope':grant.geographic_scope if grant else 'Province','status':grant.status if grant else 'Inactive',
      'permissions':perms
    }

def has(p,key): return p.get('status')=='Active' and p.get('permissions',{}).get(key) is True

def allowed(p,record):
    if p.get('status')!='Active': return False
    scope=p.get('geographic_scope')
    if scope=='Nationwide': return True
    rec_province=getattr(record,'province','') or ''
    rec_city=getattr(record,'regency_city','') or ''
    if not p.get('province') or p.get('province')!=rec_province: return False
    if scope=='Regency/City': return bool(p.get('regency_city')) and p.get('regency_city')==rec_city
    return True

def audit(db,p,subject_type,subject_id,action,changes=None):
    from datetime import datetime, timezone
    e=AuditEvent(subject_type=subject_type,subject_id=str(subject_id),action=action,actor_id=p.get('id','system'),actor_name=p.get('name','system'),changes_json=json.dumps(changes or {},ensure_ascii=False),occurred_at=datetime.now(timezone.utc).isoformat())
    db.add(e); db.commit(); return e
