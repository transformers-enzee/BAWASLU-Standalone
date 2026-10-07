import hashlib, hmac, os, secrets
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, SessionToken

def hash_password(password:str)->str:
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200_000).hex()
    return f'{salt}${digest}'

def verify_password(password:str, stored:str)->bool:
    try:
        salt,digest=stored.split('$',1)
    except ValueError:
        return False
    actual=hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(actual,digest)

def create_session(db:Session,user:User)->str:
    token=secrets.token_urlsafe(40)
    db.add(SessionToken(token=token,user_id=user.id)); db.commit()
    return token

def current_user(authorization:str|None=Header(default=None), db:Session=Depends(get_db))->User:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401,'Unauthorized')
    token=authorization.split(' ',1)[1]
    s=db.get(SessionToken,token)
    if not s: raise HTTPException(401,'Unauthorized')
    user=db.get(User,s.user_id)
    if not user: raise HTTPException(401,'Unauthorized')
    return user
