"""Idempotent Base44 JSON export importer for BAWASLU Standalone v0.1.

Expected input directory: one JSON file per entity, e.g. IntelligenceItem.json.
Each file may contain a JSON array or {"items": [...]} / {"data": [...]}.
Every raw record is staged before commit and retained verbatim for traceability.
"""
import argparse, json, pathlib, secrets
from datetime import datetime
from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .models import *
from .auth import hash_password

ENTITY_ORDER=['User','AccessGrant','IssueCategory','DataSource','ExternalDataConnector','WatchlistItem','SourceAccount','EntityRelationship','IntelligenceSequence','IntelligenceItem','TriageGeneration','EvidenceFile','AuditEvent']
TARGET_KIND={x:x for x in ENTITY_ORDER}

def load_records(path:pathlib.Path):
    if not path.exists(): return []
    obj=json.loads(path.read_text())
    if isinstance(obj,list): return obj
    if isinstance(obj,dict):
        for key in ('items','data','records','results'):
            if isinstance(obj.get(key),list): return obj[key]
    raise ValueError(f'Unsupported export shape: {path}')

def ext_id(r): return str(r.get('id') or r.get('_id') or r.get('uuid') or '')
def jd(v): return json.dumps(v if v is not None else {},ensure_ascii=False)
def sval(r,k,default=''): return str(r.get(k) if r.get(k) is not None else default)

def stage(db:Session, directory:pathlib.Path, dry_run=True):
    batch=MigrationBatch(source_label=str(directory),dry_run=dry_run,status='staged'); db.add(batch); db.commit(); db.refresh(batch)
    count=errors=0
    for entity in ENTITY_ORDER:
        path=directory/f'{entity}.json'
        try: rows=load_records(path)
        except Exception as e:
            errors+=1; continue
        for r in rows:
            rid=ext_id(r)
            rec=MigrationStagingRecord(batch_id=batch.id,source_entity=entity,source_record_id=rid,target_kind=TARGET_KIND[entity],payload_json=json.dumps(r,ensure_ascii=False),validation_status='valid' if rid or entity=='IntelligenceSequence' else 'warning',validation_errors_json='[]' if rid or entity=='IntelligenceSequence' else '["missing source id"]')
            db.add(rec); count+=1
    batch.record_count=count; batch.error_count=errors; batch.summary_json=json.dumps({'entities':ENTITY_ORDER,'records':count,'file_errors':errors}); db.commit()
    return batch

def lookup_ext(db, model, external_id):
    if not external_id: return None
    return db.query(model).filter(model.external_id==str(external_id)).first()

def commit_record(db, rec):
    r=json.loads(rec.payload_json); eid=ext_id(r); entity=rec.source_entity; obj=None
    if entity=='User':
        email=sval(r,'email',f'imported-{eid}@invalid.local').lower(); obj=db.query(User).filter(User.email==email).first()
        if not obj: obj=User(email=email,full_name=sval(r,'full_name',sval(r,'name','')),password_hash=hash_password(secrets.token_urlsafe(32)),platform_admin=(r.get('role')=='admin')); db.add(obj)
    elif entity=='AccessGrant':
        user_ext=sval(r,'user_id'); user=lookup_ext(db,ImportedIdentity,user_ext) if False else None
        # Base44 User IDs are resolved by email only when export carries embedded email; otherwise stage stays traceable.
        uid=r.get('_resolved_user_id')
        if not uid:
            source_users=db.query(MigrationStagingRecord).filter(MigrationStagingRecord.batch_id==rec.batch_id,MigrationStagingRecord.source_entity=='User',MigrationStagingRecord.source_record_id==user_ext).all()
            if source_users:
                ur=json.loads(source_users[0].payload_json); u=db.query(User).filter(User.email==sval(ur,'email').lower()).first(); uid=u.id if u else None
        if not uid: raise ValueError(f'AccessGrant user_id {user_ext} unresolved')
        obj=db.query(AccessGrant).filter(AccessGrant.user_id==uid).first() or AccessGrant(user_id=uid); db.add(obj)
        obj.access_role=sval(r,'access_role','Viewer'); obj.province=sval(r,'province'); obj.regency_city=sval(r,'regency_city'); obj.geographic_scope=sval(r,'geographic_scope','Province'); obj.permissions_json=jd(r.get('permissions') or {}); obj.status=sval(r,'status','Active')
    elif entity=='IssueCategory':
        obj=lookup_ext(db,IssueCategory,eid) or db.query(IssueCategory).filter(IssueCategory.name==sval(r,'name')).first() or IssueCategory(external_id=eid,name=sval(r,'name')); db.add(obj); obj.external_id=obj.external_id or eid; obj.active=bool(r.get('active',True)); obj.sort_order=int(r.get('sort_order') or 0)
    elif entity=='DataSource':
        obj=lookup_ext(db,DataSource,eid) or DataSource(external_id=eid); db.add(obj)
        for k in ('name','source_type','description','status','province','regency_city'): setattr(obj,k,sval(r,k,'Active' if k=='status' else ''))
    elif entity=='ExternalDataConnector':
        obj=lookup_ext(db,ExternalDataConnector,eid) or db.query(ExternalDataConnector).filter(ExternalDataConnector.connector_id==sval(r,'connector_id',eid)).first() or ExternalDataConnector(external_id=eid,connector_id=sval(r,'connector_id',eid)); db.add(obj); obj.external_id=obj.external_id or eid; obj.provider_name=sval(r,'provider_name'); obj.connector_type=sval(r,'connector_type'); obj.status=sval(r,'status','DISABLED'); obj.supported_sources_json=jd(r.get('supported_sources') or []); obj.configuration_json=jd(r.get('configuration') or {}); obj.last_sync=sval(r,'last_sync'); obj.health_status=sval(r,'health_status')
    elif entity=='WatchlistItem':
        obj=lookup_ext(db,WatchlistItem,eid) or WatchlistItem(external_id=eid,name=sval(r,'name')); db.add(obj)
        for k in ('name','type','description','province','regency_city','related_election','related_entity','priority','status','notes'): setattr(obj,k,sval(r,k,'Medium' if k=='priority' else 'Active' if k=='status' else ''))
        obj.related_topics_json=jd(r.get('related_topics') or [])
    elif entity=='SourceAccount':
        w=lookup_ext(db,WatchlistItem,sval(r,'watchlist_id'))
        if not w: raise ValueError('SourceAccount watchlist unresolved')
        obj=lookup_ext(db,SourceAccount,eid) or SourceAccount(external_id=eid,watchlist_id=w.id,url=sval(r,'url')); db.add(obj); obj.watchlist_id=w.id; obj.url=sval(r,'url'); obj.platform=sval(r,'platform'); obj.handle=sval(r,'handle'); obj.province=sval(r,'province'); obj.regency_city=sval(r,'regency_city')
    elif entity=='EntityRelationship':
        f=lookup_ext(db,WatchlistItem,sval(r,'from_id')); t=lookup_ext(db,WatchlistItem,sval(r,'to_id'))
        if not f or not t: raise ValueError('EntityRelationship endpoint unresolved')
        obj=lookup_ext(db,EntityRelationship,eid) or EntityRelationship(external_id=eid,from_id=f.id,to_id=t.id,relationship_type=sval(r,'relationship_type')); db.add(obj); obj.from_id=f.id; obj.to_id=t.id; obj.relationship_type=sval(r,'relationship_type'); obj.province=sval(r,'province')
    elif entity=='IntelligenceSequence':
        year=int(r.get('year') or datetime.utcnow().year); obj=db.get(IntelligenceSequence,year) or IntelligenceSequence(year=year,sequence=0); db.add(obj); obj.sequence=max(obj.sequence,int(r.get('sequence') or 0))
    elif entity=='IntelligenceItem':
        obj=lookup_ext(db,IntelligenceItem,eid) or db.query(IntelligenceItem).filter(IntelligenceItem.intelligence_id==sval(r,'intelligence_id')).first() or IntelligenceItem(external_id=eid,intelligence_id=sval(r,'intelligence_id',f'LEGACY-{eid}')); db.add(obj); obj.external_id=obj.external_id or eid
        scalar=['title','original_content','original_language','original_language_code','english_translation','future_indonesian_translation','ai_summary','ai_analysis','source_type','ingestion_method','observed_publisher_handle','source_id','source_url','source_name','platform','author','publication_datetime','publication_date','publication_time_precision','collection_datetime','jurisdiction_type','jurisdiction_confirmed_by','jurisdiction_confirmed_at','jurisdiction_source','province','regency_city','province_code','regency_city_code','location_text','potential_issue_category','analyst_notes','reason','evidence_state','evidence_type','verification_status','review_status','confidence','priority','assigned_reviewer','review_notes','validated_at','duplicate_of','duplicate_resolution','merged_into','watchlist_id']
        for k in scalar: setattr(obj,k,sval(r,k,getattr(obj,k,'')))
        obj.jurisdiction_confirmed=bool(r.get('jurisdiction_confirmed',False))
        for key,col,default in [('ai_suggestions','ai_suggestions_json',{}),('ai_geography','ai_geography_json',{}),('proposed_geography','proposed_geography_json',{}),('geographic_mismatch_review','geographic_mismatch_review_json',{}),('provider_source_metadata','provider_source_metadata_json',{}),('source_identity','source_identity_json',{}),('entity_relationships','entity_relationships_json',[]),('owned_channel','owned_channel_json',{}),('related_entities','related_entities_json',[]),('related_topics','related_topics_json',[]),('geographic_assignments','geographic_assignments_json',[]),('intelligence_extraction','intelligence_extraction_json',{}),('supervision_screening','supervision_screening_json',{})]: setattr(obj,col,jd(r.get(key) if key in r else default))
    elif entity=='TriageGeneration':
        item=lookup_ext(db,IntelligenceItem,sval(r,'intelligence_item_id'))
        run=sval(r,'triage_run_id',eid); obj=lookup_ext(db,TriageGeneration,eid) or db.query(TriageGeneration).filter(TriageGeneration.triage_run_id==run).first() or TriageGeneration(external_id=eid,triage_run_id=run); db.add(obj); obj.external_id=obj.external_id or eid; obj.intelligence_item_id=item.id if item else None
        for k in ('initiated_by_id','source_fingerprint','proposal_fingerprint','generator','generator_version','service_action','attempt_started_at','attempt_ended_at','generated_at','validation_outcome'): setattr(obj,k,sval(r,k))
        obj.triage_schema_version=int(r.get('triage_schema_version') or 3); obj.rejected_fields_json=jd(r.get('rejected_fields') or []); obj.proposal_field_names_json=jd(r.get('proposal_field_names') or [])
    elif entity=='EvidenceFile':
        item=lookup_ext(db,IntelligenceItem,sval(r,'intelligence_item_id'))
        if not item: raise ValueError('EvidenceFile intelligence item unresolved')
        obj=lookup_ext(db,EvidenceFile,eid) or EvidenceFile(external_id=eid,intelligence_item_id=item.id,file_uri=sval(r,'file_uri'),original_filename=sval(r,'original_filename')); db.add(obj); obj.intelligence_item_id=item.id
        for k in ('file_uri','original_filename','file_type','uploaded_by','uploaded_at','related_entity','related_location','description','evidence_state'): setattr(obj,k,sval(r,k))
    elif entity=='AuditEvent':
        obj=db.query(AuditEvent).filter(AuditEvent.external_id==eid).first() if eid else None
        if not obj: obj=AuditEvent(external_id=eid or None,subject_type=sval(r,'subject_type'),subject_id=sval(r,'subject_id'),action=sval(r,'action')); db.add(obj)
        obj.actor_id=sval(r,'actor_id'); obj.actor_name=sval(r,'actor_name'); obj.changes_json=jd(r.get('changes') or {}); obj.occurred_at=sval(r,'occurred_at')
    else: raise ValueError(f'Unsupported entity {entity}')
    db.flush(); rec.committed_entity_id=str(getattr(obj,'id',getattr(obj,'year',''))); rec.validation_status='committed'; return obj

def commit_batch(db:Session,batch_id:int):
    batch=db.get(MigrationBatch,batch_id); errors=[]
    if not batch: raise ValueError('Batch not found')
    for entity in ENTITY_ORDER:
        rows=db.query(MigrationStagingRecord).filter(MigrationStagingRecord.batch_id==batch_id,MigrationStagingRecord.source_entity==entity).order_by(MigrationStagingRecord.id).all()
        for rec in rows:
            try: commit_record(db,rec); db.commit()
            except Exception as e: db.rollback(); rec=db.get(MigrationStagingRecord,rec.id); rec.validation_status='error'; rec.validation_errors_json=json.dumps([str(e)]); db.commit(); errors.append({'entity':entity,'source_record_id':rec.source_record_id,'error':str(e)})
    batch=db.get(MigrationBatch,batch_id); batch.status='committed_with_errors' if errors else 'committed'; batch.error_count=len(errors); batch.dry_run=False; batch.summary_json=json.dumps({'records':batch.record_count,'errors':errors},ensure_ascii=False); db.commit(); return batch,errors

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('directory'); ap.add_argument('--commit',action='store_true'); args=ap.parse_args()
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        batch=stage(db,pathlib.Path(args.directory),dry_run=not args.commit); print(json.dumps({'batch_id':batch.id,'record_count':batch.record_count,'error_count':batch.error_count,'dry_run':batch.dry_run}))
        if args.commit:
            batch,errors=commit_batch(db,batch.id); print(json.dumps({'status':batch.status,'errors':errors},ensure_ascii=False))
    finally: db.close()
if __name__=='__main__': main()
