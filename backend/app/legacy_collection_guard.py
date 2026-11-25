"""Durable legacy campaign collection claims, independent of provider billing.

Use the existing run/edge tables (no schema changes). A guard records a batch,
not a provider request; its child runs retain the actual credit receipts.
All start/edit/remove operations serialize against the campaign row.
"""
import json
from datetime import datetime,timezone,timedelta
from .models import SocialListeningRun,CampaignRun
from .access import allowed
from .prism_collection_budget import meta_for

PROVIDER='SOCIALCRAWL_MANUAL_BATCH'

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def stale(run):
    try:stamp=datetime.fromisoformat(meta_for(run).get('heartbeat_at',''))
    except (ValueError,TypeError):stamp=run.executed_at
    if stamp and stamp.tzinfo:stamp=stamp.astimezone(timezone.utc).replace(tzinfo=None)
    return run.status=='RUNNING' and bool(stamp and now()-stamp>timedelta(minutes=90))

def latest(db,c):
    return (db.query(SocialListeningRun).join(CampaignRun,CampaignRun.social_listening_run_id==SocialListeningRun.id)
        .filter(CampaignRun.campaign_id==c.id,SocialListeningRun.provider==PROVIDER)
        .order_by(SocialListeningRun.id.desc()).first())

def view(db,c):
    run=latest(db,c)
    if not run:return None
    meta=meta_for(run)
    return {'run_id':str(run.id),'status':run.status,'stale':stale(run),
            'completed_searches':len(meta.get('completed_run_ids',[])),
            'planned_searches':meta.get('planned_searches',0),
            'uncertain':bool(meta.get('uncertain')),'error':run.error_text or '',
            'paid_provider_called':False}

def begin(db,c,p,snapshot,revision,planned):
    from .prism_discover import ensure_no_active_collection
    ensure_no_active_collection(db,c.id)
    run=SocialListeningRun(provider=PROVIDER,status='RUNNING',executed_by=str(p.get('id') or ''),
        query_json=json.dumps({'campaign_id':c.id,'search_snapshot':snapshot,'query_revision':revision,
            'province':c.province,'regency_city':c.regency_city,'planned_searches':planned,
            'completed_run_ids':[],'heartbeat_at':now().isoformat(),'uncertain':False}))
    db.add(run);db.flush()
    db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=run.id,triggered_by='MANUAL_BATCH'))
    db.commit()
    return run.id

def checkpoint(db,run_id,child_id=None,persist=True,submitting=False):
    run=db.query(SocialListeningRun).filter_by(id=int(run_id),provider=PROVIDER).populate_existing().with_for_update().first()
    if not run or run.status!='RUNNING':raise ValueError('Legacy collection claim is no longer active; no further paid request is allowed')
    meta=meta_for(run)
    meta['heartbeat_at']=now().isoformat()
    if submitting:meta['uncertain']=True
    if child_id is not None:
        meta['completed_run_ids']=list(dict.fromkeys(meta.get('completed_run_ids',[])+[int(child_id)]))
        meta['uncertain']=False
    run.query_json=json.dumps(meta)
    if persist:db.commit()
    return run,meta

def finish(db,run_id,status,linked=0,error=''):
    run=db.query(SocialListeningRun).filter_by(id=int(run_id),provider=PROVIDER).populate_existing().with_for_update().first()
    if not run or run.status!='RUNNING':
        db.rollback();return
    meta=meta_for(run)
    meta['heartbeat_at']=now().isoformat()
    run.query_json=json.dumps(meta);run.status=status;run.result_count=linked;run.error_text=str(error)[:500]
    db.commit()

def quarantine(db,c,p,data):
    from .prism_discover import locked_campaign
    from .campaigns import _editable
    c=locked_campaign(db,c.id)
    if not c or not allowed(p,c) or not _editable(p,c):raise PermissionError('Campaign owner or administrator required')
    run=latest(db,c)
    if not run or str(run.id)!=str(data.get('run_id')) or not stale(run):
        raise ValueError('Legacy collection is not stale; refresh status')
    if data.get('confirm_uncertain') is not True:raise ValueError('Confirm that a provider charge may remain unknown')
    run=db.query(SocialListeningRun).filter_by(id=run.id).populate_existing().with_for_update().first()
    if not stale(run):raise ValueError('Legacy collection worker is still active')
    meta=meta_for(run);meta['uncertain']=True;meta['quarantined']=True
    run.query_json=json.dumps(meta);run.status='FAILED'
    run.error_text='Stale legacy batch quarantined. No replacement provider request was sent.'
    # Release active storage reservations for abandoned child requests, while
    # keeping unknown upstream consumption reserved in the monthly ledger.
    for child in (db.query(SocialListeningRun).join(CampaignRun,CampaignRun.social_listening_run_id==SocialListeningRun.id)
        .filter(CampaignRun.campaign_id==c.id,SocialListeningRun.provider=='SOCIALCRAWL',SocialListeningRun.status=='RUNNING').all()):
        info=meta_for(child)
        if info.get('legacy_batch_id')!=run.id:continue
        receipt=info.get('legacy_collection') or {}
        receipt['submission_uncertain']=True;info['legacy_collection']=receipt
        child.query_json=json.dumps(info);child.status='FAILED'
        child.error_text='Parent legacy collection quarantined; provider receipt may be incomplete.'
    db.commit()
    return {'quarantined':True,'paid_provider_called':False,'legacy_batch':view(db,c)}
