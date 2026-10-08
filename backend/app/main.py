import os, shutil, uuid
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import User, SessionToken
from .auth import current_user, verify_password, create_session, hash_password
from .access import profile
from .domain import intelligence_action
from .registry import registry_action
from .socialcrawl import social_listening_action
from .source_retrieval import _language_detection
from .seed import seed

app=FastAPI(title='BAWASLU Intelligence Standalone',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173').split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','./uploads')); UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
app.mount('/uploads',StaticFiles(directory=str(UPLOAD_DIR)),name='uploads')

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)
    from .db import SessionLocal
    db=SessionLocal()
    try: seed(db)
    finally: db.close()

class LoginIn(BaseModel): email:str; password:str
class RegisterIn(BaseModel): email:str; password:str; full_name:str=''
class FunctionIn(BaseModel): action:str; data:dict={}; id:str|None=None

@app.get('/api/health')
def health(): return {'ok':True,'product':'bawaslu','version':'0.1.0','architecture_baseline':'NK Intelligence / GovIntel v0.27'}

@app.post('/api/auth/login')
def login(body:LoginIn,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.email==body.email.lower()).first()
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,'Invalid email or password')
    return {'access_token':create_session(db,user),'user':{'id':str(user.id),'email':user.email,'full_name':user.full_name,'role':'admin' if user.platform_admin else 'user'}}

@app.post('/api/auth/register')
def register(body:RegisterIn,db:Session=Depends(get_db)):
    if db.query(User).filter(User.email==body.email.lower()).first(): raise HTTPException(409,'Account already exists')
    u=User(email=body.email.lower(),full_name=body.full_name,password_hash=hash_password(body.password)); db.add(u); db.commit(); db.refresh(u)
    return {'ok':True,'message':'Account created. An administrator must assign BAWASLU access before use.'}

@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return {'id':str(user.id),'email':user.email,'full_name':user.full_name,'role':'admin' if user.platform_admin else 'user'}

@app.post('/api/auth/logout')
def logout(user:User=Depends(current_user),db:Session=Depends(get_db)):
    db.query(SessionToken).filter(SessionToken.user_id==user.id).delete(); db.commit(); return {'ok':True}

@app.get('/api/public-settings')
def public_settings(): return {'id':'bawaslu-standalone','public_settings':{'name':'BAWASLU Intelligence','registration_enabled':True,'google_login_enabled':False}}

@app.post('/api/functions/intelligence')
def intelligence(body:FunctionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    try: return intelligence_action(db,p,body.action,body.data,body.id)
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: raise HTTPException(400,str(e))

@app.post('/api/functions/registry')
def registry(body:FunctionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    try: return registry_action(db,p,body.action,body.data,body.id)
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: raise HTTPException(400,str(e))

@app.post('/api/functions/socialListening')
def social_listening(body:FunctionIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    try: return social_listening_action(db,p,body.action,body.data,body.id)
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: raise HTTPException(400,str(e))

@app.post('/api/upload')
def upload(file:UploadFile=File(...),user:User=Depends(current_user)):
    ext=Path(file.filename or '').suffix.lower().lstrip('.')
    if ext not in {'pdf','docx','xlsx','csv','png','jpg','jpeg','webp'}: raise HTTPException(400,'Approved file required')
    name=f'{uuid.uuid4().hex}_{Path(file.filename or "upload").name}'; path=UPLOAD_DIR/name
    with path.open('wb') as out: shutil.copyfileobj(file.file,out)
    return {'file_uri':f'/uploads/{name}'}

@app.post('/api/functions/getMyEffectiveAccess')
def effective_access(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    return {'access':profile(db,user)}

@app.post('/api/functions/suggestSourceLanguage')
def suggest_language(body:dict,user:User=Depends(current_user)):
    content=str(body.get('content',''))
    detection=_language_detection(content,str(body.get('declared_language') or ''))
    return {
      'language_code':detection.get('code') or 'unknown',
      'language_label':detection.get('label') or 'Unknown',
      'confidence':detection.get('confidence') or 'LOW',
      'method':detection.get('method') or 'UNRESOLVED',
      'scores':detection.get('scores') or {}
    }

@app.post('/api/functions/assistIntelligence')
def assist_intelligence(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    import hashlib, json, uuid
    from datetime import datetime, timezone
    text=str(body.get('content',''))
    run_id=str(uuid.uuid4())
    facts=[]
    for label,key in [('Platform','platform'),('Observed publisher (not ownership)','publisher'),('Original URL','source_url'),('Recorded publication','publication'),('Recorded original language','language'),('Intake source type','source_type')]:
        if body.get(key): facts.append(f'{label}: {body.get(key)}')
    suggestions={
      'summary':(text[:500] if text else str(body.get('title',''))) or 'Source submitted for human triage review.',
      'english_translation':'','content_type':'','supervision_signal':'NO SIGNAL IDENTIFIED','signal_reason':'',
      'screening_confidence':'Low','priority':'Medium','evidence_type':'OBSERVED','confidence':'Low',
      'activity':'','actors':'','location_signal':'','narrative':'','relationships':'','topics':'','evidence_gaps':'',
      'inferences':'','check_next':'','screening_evidence_basis':'','_version':3,'source_facts':'\n'.join(facts)
    }
    source_fp=hashlib.sha256((text+'|'+str(body.get('source_url',''))).encode()).hexdigest()
    proposal_fp=hashlib.sha256(json.dumps(suggestions,sort_keys=True).encode()).hexdigest()
    from .models import TriageGeneration
    g=TriageGeneration(triage_run_id=run_id,initiated_by_id=str(user.id),source_fingerprint=source_fp,proposal_fingerprint=proposal_fp,triage_schema_version=3,generator='standalone-local',generator_version='v0.1',service_action='intakePreview',generated_at=datetime.now(timezone.utc).isoformat(),validation_outcome='GENERATED',proposal_field_names_json=json.dumps(list(suggestions)))
    db.add(g); db.commit()
    return {'suggestions':suggestions,'generation':{'triage_run_id':run_id,'triage_schema_version':3,'generator':'standalone-local','generator_version':'v0.1','service_action':'intakePreview','generated_at':g.generated_at,'proposal_field_names':list(suggestions)},'geography':{},'watchlist_match':None}

@app.post('/api/functions/intelligenceAssistant')
def intelligence_assistant(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .domain import list_intelligence
    from .intelligence_assistant import (
      select_assistant_records,assistant_evidence_record,assistant_record_view,assistant_query_semantics,
      generate_openai_assistant_answer,format_assistant_answer,deterministic_assistant_answer,
      AssistantProviderError
    )
    p=profile(db,user)
    q=str(body.get('question','')).strip()
    if not q: raise HTTPException(400,'Question is required')
    if len(q)>500: raise HTTPException(400,'Question is too long')
    previous=str(body.get('previousQuestion','')).strip()[:500]
    accessible=list_intelligence(db,p)
    selected=select_assistant_records(q,accessible,limit=12)
    evidence=[assistant_evidence_record(x) for x in selected]
    provider={'mode':'DETERMINISTIC_FALLBACK','model':'','fallback_code':''}
    cited_ids=[]
    try:
        if not os.getenv('OPENAI_API_KEY','').strip():
            raise AssistantProviderError('not_configured','OpenAI is not configured')
        result,provider=generate_openai_assistant_answer(q,previous,evidence)
        allowed_ids={r['record_id'] for r in evidence}
        cited_ids=[x for x in (result.get('cited_record_ids') or []) if x in allowed_ids]
        answer=format_assistant_answer(result)
    except AssistantProviderError as exc:
        fallback=deterministic_assistant_answer(q,evidence,exc.code)
        answer=fallback['answer']; cited_ids=fallback['cited_record_ids']
        provider={'mode':'DETERMINISTIC_FALLBACK','model':'','fallback_code':exc.code}
    selected_by_id={x.intelligence_id:x for x in selected}
    support=[assistant_record_view(selected_by_id[x]) for x in cited_ids if x in selected_by_id]
    if not support:
        support=[assistant_record_view(x) for x in selected[:6]]
    semantics=assistant_query_semantics(q)
    return {'answer':answer,'records':support,'provider':provider,'grounding':{'accessible_count':len(accessible),'selected_count':len(selected),'supporting_count':len(support),'scope':'CURRENT_USER_AUTHORIZED_RECORDS_ONLY','date_basis':semantics['date_basis'],'date_basis_label':semantics['date_basis_label'],'date_basis_note':semantics['date_basis_note'],'window':semantics['window']}}

FRONTEND_DIST=Path(os.getenv('FRONTEND_DIST',Path(__file__).resolve().parents[2]/'frontend_dist'))
if FRONTEND_DIST.exists():
    ASSETS_DIR=FRONTEND_DIST/'assets'
    if ASSETS_DIR.exists():
        app.mount('/assets',StaticFiles(directory=str(ASSETS_DIR)),name='frontend-assets')

    @app.get('/{full_path:path}',include_in_schema=False)
    def frontend_spa(full_path:str):
        if full_path.startswith('api/'):
            raise HTTPException(404,'Not Found')
        candidate=FRONTEND_DIST/full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST/'index.html')
