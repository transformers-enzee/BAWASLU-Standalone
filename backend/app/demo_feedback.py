"""Demo visitor feedback. Anonymous write endpoint; authenticated national-admin read."""
from collections import Counter
from datetime import datetime,timedelta
import hashlib
import os
import re
import secrets
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from .db import get_db
from .models import DemoFeedback,User
from .auth import current_user
from .access import profile

router=APIRouter(prefix='/api/demo-feedback',tags=['demo-feedback'])
VALID_CATEGORIES={'general','usability','data','bug','suggestion'}
# Ephemeral server-side salt if an explicit secret has not been configured.
# Raw visitor IPs, headers and email addresses are never stored.
HASH_SECRET=os.getenv('DEMO_FEEDBACK_HASH_SECRET') or secrets.token_hex(32)

class FeedbackIn(BaseModel):
    category:str
    rating:int|None=Field(default=None,ge=1,le=5)
    message:str=Field(min_length=10,max_length=1500)
    page_path:str=Field(default='/demo',max_length=255)
    language:str=Field(default='id',pattern='^(id|en)$')
    website:str=Field(default='',max_length=200)  # hidden anti-bot honeypot

def require_admin(db,user):
    p=profile(db,user)
    if not (p.get('status')=='Active' and p.get('role')=='National Administrator'
            and p.get('permissions',{}).get('administration') is True):
        raise HTTPException(403,'National administrator required')

def hash_visitor(request,now):
    # Never trust unvalidated X-Forwarded-For headers supplied by visitors.
    address=request.client.host if request.client else 'unknown'
    return hashlib.sha256((HASH_SECRET+'|'+now.strftime('%Y-%m-%d')+'|'+address).encode()).hexdigest()

@router.post('',status_code=201)
def submit_feedback(body:FeedbackIn,request:Request,db:Session=Depends(get_db)):
    if body.website:raise HTTPException(400,'Invalid submission')
    if body.category not in VALID_CATEGORIES:raise HTTPException(422,'Invalid feedback category')
    message=body.message.strip()
    if len(message)<10 or len(message)>1500:raise HTTPException(422,'Feedback must be 10-1500 characters')
    if not re.fullmatch(r'/demo(?:/[a-zA-Z0-9/_-]*)?',body.page_path):
        raise HTTPException(422,'Invalid demo page')
    now=datetime.utcnow()
    visitor_hash=hash_visitor(request,now)
    recent=(db.query(DemoFeedback)
        .filter(DemoFeedback.visitor_hash==visitor_hash,
                DemoFeedback.created_at>=now-timedelta(minutes=10)).count())
    if recent>=3:raise HTTPException(429,'Too many submissions. Try again later.')
    daily=(db.query(DemoFeedback).filter(DemoFeedback.visitor_hash==visitor_hash,
        DemoFeedback.created_at>=now-timedelta(hours=24)).count())
    if daily>=12:raise HTTPException(429,'Daily feedback limit reached')
    # Reject same payload repeatedly in a single day.
    duplicate=db.query(DemoFeedback.id).filter(
        DemoFeedback.visitor_hash==visitor_hash,DemoFeedback.message==message,
        DemoFeedback.created_at>=now-timedelta(hours=24)).first()
    if duplicate:raise HTTPException(409,'Feedback already submitted')
    db.add(DemoFeedback(category=body.category,rating=body.rating,
        message=message,page_path=body.page_path,language=body.language,
        visitor_hash=visitor_hash,created_at=now))
    db.commit()
    return {'ok':True,'message':'Feedback received'}

@router.get('/admin')
def list_feedback(db:Session=Depends(get_db),user:User=Depends(current_user)):
    require_admin(db,user)
    rows=db.query(DemoFeedback).order_by(DemoFeedback.created_at.desc(),DemoFeedback.id.desc()).all()
    rating=[r.rating for r in rows if r.rating is not None]
    return {'total':len(rows),'average_rating':round(sum(rating)/len(rating),2) if rating else None,
        'rated_count':len(rating),
        'by_category':dict(Counter(r.category for r in rows)),
        'by_page':dict(Counter(r.page_path for r in rows)),
        'recent':[{'id':r.id,'category':r.category,'rating':r.rating,
                   'message':r.message,'page_path':r.page_path,
                   'language':r.language,'created_at':r.created_at.isoformat()+'Z'}
                  for r in rows[:200]]}
