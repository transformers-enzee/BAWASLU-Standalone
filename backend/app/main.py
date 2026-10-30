import os, shutil, uuid
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
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
from .socialcrawl import social_listening_action, recover_existing_news_languages, sync_promoted_news_languages
from .source_retrieval import _language_detection
from .smart_radar import router as smart_radar_router
from .issue_distribution import router as issue_distribution_router
from .assistant_history import router as assistant_history_router
from .integration_readiness import router as integration_readiness_router
from .source_lineage import router as source_lineage_router
from .deployment_readiness import router as deployment_readiness_router
from .smart_radar_processing import router as smart_radar_processing_router
from .smart_radar_synthesis import router as smart_radar_synthesis_router
from .smart_radar_qa import router as smart_radar_qa_router
from .smart_radar_calibration import router as smart_radar_calibration_router
from .smart_radar_qa_v2 import router as smart_radar_qa_v2_router
from .smart_radar_qa_tuning import router as smart_radar_qa_tuning_router
from .smart_radar_qa_alignment import router as smart_radar_qa_alignment_router
from .seed import seed

app=FastAPI(title='BAWASLU Intelligence Standalone',version='0.1.0')
app.include_router(smart_radar_router)
app.include_router(issue_distribution_router)
app.include_router(assistant_history_router)
app.include_router(integration_readiness_router)
app.include_router(source_lineage_router)
app.include_router(deployment_readiness_router)
app.include_router(smart_radar_processing_router)
app.include_router(smart_radar_synthesis_router)
app.include_router(smart_radar_qa_router)
app.include_router(smart_radar_calibration_router)
app.include_router(smart_radar_qa_v2_router)
app.include_router(smart_radar_qa_tuning_router)
app.include_router(smart_radar_qa_alignment_router)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173').split(',')],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
UPLOAD_DIR=Path(os.getenv('UPLOAD_DIR','./uploads')); UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
app.mount('/uploads',StaticFiles(directory=str(UPLOAD_DIR)),name='uploads')

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)
    from .db import SessionLocal
    db=SessionLocal()
    try:
        seed(db)
        recover_existing_news_languages(db)
        sync_promoted_news_languages(db)
    finally: db.close()
    # Optional Watchlist worker: on registration it fetches immediately, then
    # periodically while this web instance stays awake. Never start without a
    # positive administrator-controlled SocialCrawl credit budget.
    from .watchlist_auto import readiness as watchlist_readiness
    if watchlist_readiness()['enabled']:
        import logging, threading, time
        from .watchlist_auto import run_due_cycle
        def watchlist_worker_loop():
            while True:
                try:run_due_cycle()
                except Exception:logging.getLogger(__name__).exception('Watchlist sync cycle failed')
                time.sleep(60)
        threading.Thread(target=watchlist_worker_loop,
                         name='bawaslu-watchlist-worker',daemon=True).start()

    # Opt-in only: do not initiate any paid work unless BOTH controls are enabled.
    if os.getenv('BAWASLU_AUTO_AI_SCREENING_ENABLED','false').lower()=='true' and os.getenv('BAWASLU_AI_WORKER_ENABLED','false').lower()=='true':
        from .auto_relevance import recover_stale_jobs, assess_pending_campaign
        from .models import AIAssessmentJob
        import threading, time
        def worker_loop():
            while True:
                try:
                    recover_stale_jobs()
                    session=SessionLocal()
                    try:
                        campaign_ids=[row[0] for row in session.query(AIAssessmentJob.campaign_id).filter(
                            AIAssessmentJob.state=='PENDING').distinct().limit(20).all()]
                    finally:session.close()
                    for cid in campaign_ids: assess_pending_campaign(cid)
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception('AI worker cycle failed')
                time.sleep(60)
        threading.Thread(target=worker_loop,name='bawaslu-ai-worker',daemon=True).start()

    # Explicit, snapshot-bounded, user-authorized campaign sentiment run.
    # It is OFF unless two Render administrator-controlled variables match.
    from .sentiment_backfill_once import enabled as sentiment_backfill_enabled
    if sentiment_backfill_enabled():
        import threading
        from .sentiment_backfill_once import run_once as sentiment_run_once
        threading.Thread(target=sentiment_run_once,
                         name='bawaslu-sentiment-one-time',daemon=True).start()

class LoginIn(BaseModel): email:str; password:str
class RegisterIn(BaseModel): email:str; password:str; full_name:str=''
class FunctionIn(BaseModel): action:str; data:dict={}; id:str|None=None

@app.get('/api/health')
def health(): return {'ok':True,'product':'bawaslu','version':'0.1.0','build_version':'113.0','commit':os.getenv('RENDER_GIT_COMMIT',''),'architecture_baseline':'NK Intelligence / GovIntel v0.27'}

class GateIn(BaseModel):
    question:str
    active:bool=True
    required_answer:str='YES'

def _gate_admin(p):
    return p.get('status')=='Active' and p.get('role')=='National Administrator' and p.get('permissions',{}).get('administration') is True

@app.get('/api/relevance-gates')
def list_relevance_gates(user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .models import RelevanceGateQuestion
    if not _gate_admin(profile(db,user)):raise HTTPException(403,'National administrator required')
    return {'questions':[{'id':q.id,'question':q.question,'active':q.active,'required_answer':q.required_answer} for q in db.query(RelevanceGateQuestion).order_by(RelevanceGateQuestion.id).all()]}

@app.post('/api/relevance-gates')
def add_relevance_gate(body:GateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .models import RelevanceGateQuestion
    if not _gate_admin(profile(db,user)):raise HTTPException(403,'National administrator required')
    question=body.question.strip()
    if not 12<=len(question)<=400:raise HTTPException(400,'Question must contain 12 to 400 characters')
    if db.query(RelevanceGateQuestion).count()>=20:raise HTTPException(400,'Maximum 20 gate questions')
    if body.required_answer not in ('YES','NO'):raise HTTPException(400,'Required answer must be YES or NO')
    item=RelevanceGateQuestion(question=question,active=body.active,required_answer=body.required_answer)
    db.add(item);db.commit();return {'id':item.id,'question':item.question,'active':item.active,'required_answer':item.required_answer}

@app.put('/api/relevance-gates/{question_id}')
def edit_relevance_gate(question_id:int,body:GateIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .models import RelevanceGateQuestion
    if not _gate_admin(profile(db,user)):raise HTTPException(403,'National administrator required')
    item=db.get(RelevanceGateQuestion,question_id)
    if not item:raise HTTPException(404,'Question not found')
    question=body.question.strip()
    if not 12<=len(question)<=400:raise HTTPException(400,'Question must contain 12 to 400 characters')
    if body.required_answer not in ('YES','NO'):raise HTTPException(400,'Required answer must be YES or NO')
    item.question=question;item.active=body.active;item.required_answer=body.required_answer;db.commit()
    return {'id':item.id,'question':item.question,'active':item.active,'required_answer':item.required_answer}

@app.delete('/api/relevance-gates/{question_id}')
def delete_relevance_gate(question_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .models import RelevanceGateQuestion
    if not _gate_admin(profile(db,user)):raise HTTPException(403,'National administrator required')
    item=db.get(RelevanceGateQuestion,question_id)
    if not item:raise HTTPException(404,'Question not found')
    db.delete(item);db.commit();return {'deleted':True}

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
def registry(body:FunctionIn,background_tasks:BackgroundTasks,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    try:
        result=registry_action(db,p,body.action,body.data,body.id)
        if body.action in ('addAccount','updateAccount') and result.get('account'):
            from .watchlist_auto import readiness, sync_account
            if readiness()['enabled']:
                background_tasks.add_task(sync_account,int(result['account']['id']))
        return result
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: raise HTTPException(400,str(e))

@app.post('/api/functions/commandCenter')
def executive_command_center(body:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
    # The dashboard is a scoped compilation, never an independent evidence store.
    from .command_center import build_command_center
    p=profile(db,user)
    try:return build_command_center(db,p,body)
    except PermissionError as e:raise HTTPException(403,str(e))
    except ValueError as e:raise HTTPException(400,str(e))

@app.post('/api/functions/socialListening')
def social_listening(body:FunctionIn,background_tasks:BackgroundTasks,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    try:
        from .inbox_read_cache import read as cached_inbox, invalidate as invalidate_inbox
        if body.action=='campaignIntelligenceInbox':
            result=cached_inbox(p,{'campaign_id':(body.data or {}).get('campaign_id'),
                'result_id':(body.data or {}).get('result_id'),'id':body.id},
                lambda:social_listening_action(db,p,body.action,body.data,body.id))
        else:
            # Evict when any campaign/source/assessment action may alter data.
            # Some actions are read-only, but conservative eviction is safe.
            if body.action not in ('campaignDashboard','campaignEvidence',
                                  'campaignFindingGroupsPreview','campaignFindingGroupsList'):
                invalidate_inbox()
            result=social_listening_action(db,p,body.action,body.data,body.id)
        if body.action=='campaignManualRun' and body.id and result.get('linked_evidence',0)>0 and os.getenv('BAWASLU_AUTO_AI_SCREENING_ENABLED','false').lower()=='true':
            from .auto_relevance import assess_pending_campaign
            background_tasks.add_task(assess_pending_campaign,int(body.id))
        if body.action in ('campaignSingleAssessmentStart','campaignSingleReanalysisStart') and result.get('single_assessment_accepted'):
            from .auto_relevance import assess_pending_campaign
            background_tasks.add_task(assess_pending_campaign,int(result['campaign_id']),1,int(result['result_id']),bool(result.get('reanalysis')))
        if body.action=='campaignAssessmentBacklogStart' and result.get('assessment_job_accepted'):
            from .auto_relevance import assess_pending_campaign
            background_tasks.add_task(assess_pending_campaign,int(result['campaign_id']),int(result['batch_limit']))
        if body.action=='campaignAssessmentPilotStart' and result.get('started'):
            from .assessment_pilot import execute_assessment_pilot
            background_tasks.add_task(execute_assessment_pilot,int(result['campaign_id']),result['batch_result_ids'])
        return result
    except PermissionError as e: raise HTTPException(403,str(e))
    except ValueError as e: raise HTTPException(400,str(e))



@app.post('/api/social-listening/human-verified/preview')
async def preview_human_verified_import(campaign_id:int,file:UploadFile=File(...),
                                       user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .access import allowed,has
    from .models import MonitoringCampaign
    from .human_verified_import import preview,MAX_BYTES
    p=profile(db,user);campaign=db.get(MonitoringCampaign,campaign_id)
    if not campaign or not allowed(p,campaign):raise HTTPException(404,'Campaign unavailable')
    if p.get('role')!='National Administrator' or not has(p,'administration'):
        raise HTTPException(403,'National administrator permission required')
    if Path(file.filename or '').suffix.lower()!='.xlsx':
        raise HTTPException(400,'Upload a human-reviewed .xlsx workbook')
    content=await file.read(MAX_BYTES+1)
    try:return {'campaign_id':campaign_id,'preview_only':True,**preview(content)}
    except ValueError as e:raise HTTPException(400,str(e))

@app.post('/api/social-listening/human-verified/start')
async def import_human_verified_workbook(campaign_id:int,file:UploadFile=File(...),
                                         user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .access import allowed,has
    from .models import MonitoringCampaign
    from .human_verified_import import import_rows,MAX_BYTES
    p=profile(db,user);campaign=db.get(MonitoringCampaign,campaign_id)
    if not campaign or not allowed(p,campaign):raise HTTPException(404,'Campaign unavailable')
    if p.get('role')!='National Administrator' or not has(p,'administration'):
        raise HTTPException(403,'National administrator permission required')
    if Path(file.filename or '').suffix.lower()!='.xlsx':
        raise HTTPException(400,'Upload a human-reviewed .xlsx workbook')
    content=await file.read(MAX_BYTES+1)
    try:
        return {'campaign_id':campaign_id,**import_rows(db,campaign,content,user.id)}
    except ValueError as e:
        db.rollback()
        raise HTTPException(400,str(e))
    except Exception:
        db.rollback()
        raise

@app.post('/api/social-listening/external-import/preview')
def preview_external_campaign_import(campaign_id:int,file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Admin-only, read-only preview. Never saves imported evidence."""
    from .access import has, allowed
    from .models import MonitoringCampaign
    from .external_import_preview import preview_workbook
    from .campaigns import _editable
    p=profile(db,user)
    campaign=db.get(MonitoringCampaign,campaign_id)
    if not campaign or not allowed(p,campaign):
        raise HTTPException(404,'Campaign unavailable')
    if not (p.get('role')=='National Administrator' and has(p,'administration')):
        raise HTTPException(403,'National administrator permission required for external provider imports')
    if Path(file.filename or '').suffix.lower() not in ('.xlsx','.csv'):
        raise HTTPException(400,'Upload a ZocialEye Excel or CSV export')
    import tempfile
    from fastapi.concurrency import run_in_threadpool
    import shutil
    with tempfile.TemporaryDirectory(prefix='bawaslu_import_preview_') as folder:
        path=Path(folder)/('source'+Path(file.filename or '').suffix.lower())
        with path.open('wb') as dest:
            shutil.copyfileobj(file.file,dest)
        if path.stat().st_size>100*1024*1024:
            raise HTTPException(413,'Preview file limit is 100 MB')
        try:
            result=preview_workbook(path)
            from .external_import_preview import validate_all_rows
            from .models import SocialListeningResult
            existing=(url for (url,) in db.query(SocialListeningResult.canonical_url).filter(SocialListeningResult.canonical_url!='').all())
            result.update(validate_all_rows(path,existing))
        except ValueError as exc:
            raise HTTPException(400,str(exc))
    return {'campaign_id':str(campaign.id),'campaign_name':campaign.name,'provider':'ZOCIALEYE',
            'preview_only':True,'records_inserted':0,'socialcrawl_credits':0,**result}


@app.post('/api/social-listening/external-import/start')
def start_external_campaign_import(campaign_id:int,background_tasks:BackgroundTasks,file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Explicit admin-only ingestion; no SocialCrawl calls or AI screening."""
    from .access import has, allowed
    from .models import MonitoringCampaign,SocialListeningRun
    from .external_import_ingest import run_import
    import json
    campaign=db.get(MonitoringCampaign,campaign_id)
    p=profile(db,user)
    if not campaign or not allowed(p,campaign):
        raise HTTPException(404,'Campaign unavailable')
    if p.get('role')!='National Administrator' or not has(p,'administration'):
        raise HTTPException(403,'National administrator permission required')
    from sqlalchemy import select
    active_runs=db.execute(select(SocialListeningRun).where(SocialListeningRun.provider=='ZOCIALEYE',SocialListeningRun.status.in_(['QUEUED','RUNNING']))).scalars().all()
    from datetime import datetime, timezone, timedelta
    for active in active_runs:
        try:details=json.loads(active.query_json or '{}')
        except (ValueError,TypeError):details={}
        if str(details.get('campaign_id'))!=str(campaign_id):continue
        try:heartbeat=datetime.fromisoformat(details.get('heartbeat_utc',''))
        except (ValueError,TypeError):heartbeat=active.executed_at.replace(tzinfo=timezone.utc) if active.executed_at else datetime.now(timezone.utc)
        if heartbeat.tzinfo is None:heartbeat=heartbeat.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc)-heartbeat > timedelta(minutes=45):
            active.status='INTERRUPTED'
            active.error_text='Import worker stopped responding. Reupload the same file to resume safely using provider IDs.'
            db.commit()
        else:raise HTTPException(409,'Another ZocialEye import is active. Refresh its progress before starting another.')
    ext=Path(file.filename or '').suffix.lower()
    if ext not in ('.xlsx','.csv'):raise HTTPException(400,'Excel or CSV required')
    import tempfile
    from .external_import_preview import preview_workbook
    fd,temporary_path=tempfile.mkstemp(suffix=ext,prefix='bawaslu_external_')
    os.close(fd)
    temp=Path(temporary_path)
    try:
        with temp.open('wb') as target:
            total=0
            while True:
                chunk=file.file.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>100*1024*1024:raise HTTPException(413,'100 MB maximum')
                target.write(chunk)
        result=preview_workbook(temp)
        from .external_import_preview import validate_all_rows
        result.update(validate_all_rows(temp))
        if not result['validation'].get('eligible_rows'):
            raise HTTPException(400,'No eligible rows: verify IDs, messages, platform URLs and source fields')
        if not result['mapped_fields'].get('provider_result_id') or not result['mapped_fields'].get('text_content'):
            raise HTTPException(400,'Provider ID and message columns required')
        run=SocialListeningRun(provider='ZOCIALEYE',provider_request_id=uuid.uuid4().hex,
            query_json=json.dumps({'campaign_id':campaign_id,'source_filename':Path(file.filename or '').name,
                                    'provider':'ZOCIALEYE','processed':0,'inserted':0,'linked':0,'skipped':0,'heartbeat_utc':datetime.now(timezone.utc).isoformat()}),
            credits_used=0,credits_remaining=0,result_count=0,status='QUEUED',
            executed_by=str(user.id))
        db.add(run);db.commit();db.refresh(run)
        background_tasks.add_task(run_import,run.id,campaign_id,str(temp))
        return {'run_id':run.id,'status':'QUEUED','campaign_id':campaign_id,'provider':'ZOCIALEYE','socialcrawl_credits':0}
    except Exception:
        temp.unlink(missing_ok=True)
        raise

@app.get('/api/social-listening/external-import/status/{run_id}')
def external_campaign_import_status(run_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    from .access import has
    from .models import SocialListeningRun
    import json
    p=profile(db,user)
    if p.get('role')!='National Administrator' or not has(p,'administration'):
        raise HTTPException(403,'Administrator permission required')
    run=db.get(SocialListeningRun,run_id)
    if not run or run.provider!='ZOCIALEYE':raise HTTPException(404,'Import not found')
    from datetime import datetime, timezone
    progress=json.loads(run.query_json or '{}')
    try:heartbeat=datetime.fromisoformat(progress.get('heartbeat_utc',''))
    except (TypeError,ValueError):heartbeat=None
    if heartbeat and heartbeat.tzinfo is None:heartbeat=heartbeat.replace(tzinfo=timezone.utc)
    stalled=bool(run.status=='RUNNING' and heartbeat and (datetime.now(timezone.utc)-heartbeat).total_seconds()>180)
    return {'run_id':run.id,'status':run.status,'progress':progress,'stalled':stalled,
            'error':run.error_text if run.status in ('FAILED','INTERRUPTED') else '', 'socialcrawl_credits':0}


@app.get('/api/social-listening/campaign/{campaign_id}/export.csv')
def export_campaign_evidence_csv(campaign_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Stream all campaign evidence without a browser-side row cap."""
    import csv,io,json
    from fastapi.responses import StreamingResponse
    from sqlalchemy import select
    from .access import allowed
    from .models import MonitoringCampaign,CampaignEvidence,SocialListeningResult
    campaign=db.get(MonitoringCampaign,campaign_id)
    if not campaign or not allowed(profile(db,user),campaign):raise HTTPException(404,'Campaign unavailable')
    fields=['id','provider','provider_result_id','platform','content_type','published_at','author_name',
            'canonical_url','text_content','engagement_total','likes','comments','shares','views','parent_url']
    def stream():
        output=io.StringIO()
        writer=csv.writer(output)
        writer.writerow(fields);yield '\\ufeff'+output.getvalue();output.seek(0);output.truncate(0)
        with SessionLocal() as read_db:
            statement=(select(SocialListeningResult).join(CampaignEvidence,CampaignEvidence.result_id==SocialListeningResult.id)
                       .where(CampaignEvidence.campaign_id==campaign_id).order_by(SocialListeningResult.id))
            for record in read_db.execute(statement.execution_options(yield_per=500)).scalars():
                from .campaigns import _captured_post_metrics
                metrics=_captured_post_metrics(record.engagement_json)
                try:identity=json.loads(record.source_identity_json or '{}')
                except (ValueError,TypeError):identity={}
                data={'id':record.id,'provider':record.provider,'provider_result_id':record.provider_result_id,
                      'platform':record.platform,'content_type':record.content_type,'published_at':record.published_at,
                      'author_name':record.author_name,'canonical_url':record.canonical_url,'text_content':record.text_content,
                      'parent_url':identity.get('parent_url',''),**metrics}
                writer.writerow([data.get(key,'') for key in fields])
                yield output.getvalue();output.seek(0);output.truncate(0)
    from .db import SessionLocal
    return StreamingResponse(stream(),media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition':f'attachment; filename="bawaslu_campaign_{campaign_id}_evidence.csv"',
                 'Cache-Control':'no-store'})

@app.post('/api/social-listening/campaign/{campaign_id}/repair-external-metrics')
def repair_external_metrics(campaign_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Admin-only restoration from provider raw payload; never estimates missing values."""
    from sqlalchemy import select
    from .access import allowed,has
    from .models import MonitoringCampaign,CampaignEvidence,SocialListeningResult
    from .external_import_ingest import provider_metrics
    import json
    p=profile(db,user);campaign=db.get(MonitoringCampaign,campaign_id)
    if not campaign or not allowed(p,campaign):raise HTTPException(404,'Campaign unavailable')
    if p.get('role')!='National Administrator' or not has(p,'administration'):
        raise HTTPException(403,'Administrator permission required')
    statement=(select(SocialListeningResult).join(CampaignEvidence,CampaignEvidence.result_id==SocialListeningResult.id)
        .where(CampaignEvidence.campaign_id==campaign_id,SocialListeningResult.provider=='ZOCIALEYE'))
    repaired=0
    for record in db.execute(statement).scalars():
        try:raw=json.loads(record.raw_payload_json or '{}')
        except (ValueError,TypeError):continue
        metrics=provider_metrics(raw)
        if metrics and json.loads(record.engagement_json or '{}')!=metrics:
            record.engagement_json=json.dumps(metrics);repaired+=1
    db.commit()
    return {'repaired':repaired,'campaign_id':campaign_id,'no_estimated_metrics':True}

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
