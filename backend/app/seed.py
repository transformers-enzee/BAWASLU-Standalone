import os, json
from sqlalchemy.orm import Session
from .models import User, AccessGrant, IssueCategory
from .auth import hash_password
from .access import default_permissions

def seed(db:Session):
    email=os.getenv('BAWASLU_BOOTSTRAP_ADMIN_EMAIL','admin@bawaslu.local').lower()
    password=os.getenv('BAWASLU_BOOTSTRAP_ADMIN_PASSWORD','ChangeMeNow!')
    user=db.query(User).filter(User.email==email).first()
    if not user:
        user=User(email=email,full_name='BAWASLU Administrator',password_hash=hash_password(password),platform_admin=True); db.add(user); db.flush()
        db.add(AccessGrant(user_id=user.id,access_role='National Administrator',geographic_scope='Nationwide',permissions_json=json.dumps(default_permissions('National Administrator')),status='Active'))
    if db.query(IssueCategory).count()==0:
        for i,name in enumerate(['Election Administration','Campaign','Disinformation','Electoral Violation','Public Order']): db.add(IssueCategory(name=name,active=True,sort_order=i+1))
    db.commit()
