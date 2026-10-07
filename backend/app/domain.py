import hashlib, json, re, uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from .models import *
from .serializers import *
from .access import has, allowed, audit

def now(): return datetime.now(timezone.utc).isoformat()
def jdump(v): return json.dumps(v,ensure_ascii=False)
def clean(v,n=5000): return (v.strip()[:n] if isinstance(v,str) else '')

def next_intelligence_id(db:Session):
    year=datetime.now(timezone.utc).year
    row=db.get(IntelligenceSequence,year)
    if not row:
        row=IntelligenceSequence(year=year,sequence=0); db.add(row); db.flush()
    row.sequence+=1; db.commit()
    return f'INT-{year}-{row.sequence:06d}'

def get_item(db,id):
    try: return db.get(IntelligenceItem,int(id))
    except Exception: return None

def duplicate_candidate(db, data):
    url=clean(data.get('source_url',''),2000)
    if url:
        hit=db.query(IntelligenceItem).filter(IntelligenceItem.source_url==url).order_by(IntelligenceItem.id.desc()).first()
        if hit: return hit
    title=clean(data.get('title',''),1000).lower()
    if title:
        candidates=db.query(IntelligenceItem).order_by(IntelligenceItem.id.desc()).limit(200).all()
        norm=lambda s: re.sub(r'\W+',' ',(s or '').lower()).strip()
        nt=norm(title)
        for x in candidates:
            if nt and norm(x.title)==nt: return x
    return None

def source_identity(db,data):
    url=clean(data.get('source_url',''),2000)
    parsed=urlparse(url) if url else None
    path=(parsed.path if parsed else '') or ''
    handle=''
    for pattern in [r'/@([^/?#]+)',r'/(?:user|users|profile)/([^/?#]+)']:
        m=re.search(pattern,path,re.I)
        if m: handle='@'+m.group(1); break
    if not handle and parsed and parsed.hostname:
        handle=parsed.hostname.lower().removeprefix('www.')
    accounts=db.query(SourceAccount).all()
    for a in accounts:
        if url and a.url and url.rstrip('/').startswith(a.url.rstrip('/')):
            return {'status':'REGISTERED_ACCOUNT_CONFIRMED','matched_registered_account_id':str(a.id),'match_basis':'PUBLIC_URL_PREFIX','verification_status':'CONFIRMED','verified_by':'SYSTEM_REGISTRY','verified_at':now()}, handle or a.handle
        if handle and a.handle and handle.lower()==a.handle.lower():
            return {'status':'REGISTERED_ACCOUNT_CONFIRMED','matched_registered_account_id':str(a.id),'match_basis':'OBSERVED_HANDLE','verification_status':'CONFIRMED','verified_by':'SYSTEM_REGISTRY','verified_at':now()}, handle
    if handle:
        return {'status':'KNOWN_EXTERNAL_ACCOUNT','matched_registered_account_id':'','match_basis':'OBSERVED_PUBLIC_IDENTITY','verification_status':'NOT_VERIFIED','verified_by':'','verified_at':''}, handle
    return {'status':'UNRESOLVED','matched_registered_account_id':'','match_basis':'','verification_status':'NOT_VERIFIED','verified_by':'','verified_at':''}, ''

def geography_mismatch(item):
    proposed=loads(item.proposed_geography_json,{}) or loads(item.ai_geography_json,{})
    if not proposed or not item.jurisdiction_confirmed: return {'status':'none'}
    pprov=proposed.get('province') or proposed.get('province_name') or ''
    pcity=proposed.get('regency_city') or proposed.get('regency_city_name') or ''
    mismatch=(pprov and item.province and pprov!=item.province) or (pcity and item.regency_city and pcity!=item.regency_city)
    if not mismatch: return {'status':'none'}
    review=loads(item.geographic_mismatch_review_json,{})
    if review.get('decision'): return {'status':'resolved',**review,'proposed':proposed}
    basis=proposed.get('supporting_text') or proposed.get('evidence') or ''
    fp=hashlib.sha256(f'{item.id}|{item.province}|{item.regency_city}|{pprov}|{pcity}|{basis}'.encode()).hexdigest()
    return {'status':'pending','fingerprint':fp,'proposed':proposed,'confirmed':{'province':item.province,'regency_city':item.regency_city},'supporting_text':basis}

def create_intelligence(db,p,data):
    if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
    dupe=duplicate_candidate(db,data)
    identity, observed=source_identity(db,data)
    item=IntelligenceItem(
      intelligence_id=next_intelligence_id(db), title=clean(data.get('title'),3000), original_content=clean(data.get('original_content') or data.get('description'),20000),
      original_language=clean(data.get('original_language'),100), original_language_code=clean(data.get('original_language_code'),20), english_translation=clean(data.get('english_translation'),20000),
      source_type=clean(data.get('source_type'),64), ingestion_method=clean(data.get('ingestion_method') or ({'MANUAL_LINK':'MANUAL_URL','FILE_UPLOAD':'FILE_UPLOAD'}.get(data.get('source_type'),'MANUAL_ENTRY')),64),
      observed_publisher_handle=clean(data.get('observed_publisher_handle') or observed,255), provider_source_metadata_json=jdump(data.get('provider_source_metadata') or {}), source_identity_json=jdump(data.get('source_identity') or identity),
      entity_relationships_json=jdump(data.get('entity_relationships') or []), source_id=clean(data.get('source_id'),255), source_url=clean(data.get('source_url'),2000), source_name=clean(data.get('source_name'),255),
      platform=clean(data.get('platform'),100), author=clean(data.get('author') or observed,255), publication_datetime=clean(data.get('publication_datetime'),64), publication_date=clean(data.get('publication_date'),32),
      publication_time_precision=clean(data.get('publication_time_precision') or 'UNKNOWN',32), collection_datetime=clean(data.get('collection_datetime') or now(),64), owned_channel_json=jdump(data.get('owned_channel') or {}),
      related_entities_json=jdump((data.get('related_entities') or [])[:20]), related_topics_json=jdump((data.get('related_topics') or [])[:20]), jurisdiction_type=clean(data.get('jurisdiction_type') or 'Unresolved',32),
      jurisdiction_confirmed=bool(data.get('confirm_jurisdiction') or data.get('jurisdiction_confirmed')), jurisdiction_confirmed_by=p['name'] if data.get('confirm_jurisdiction') else clean(data.get('jurisdiction_confirmed_by'),255),
      jurisdiction_confirmed_at=now() if data.get('confirm_jurisdiction') else clean(data.get('jurisdiction_confirmed_at'),64), jurisdiction_source=clean(data.get('jurisdiction_source') or ('HUMAN_INTAKE' if data.get('confirm_jurisdiction') else ''),128),
      province=clean(data.get('province'),128), regency_city=clean(data.get('regency_city'),128), province_code=clean(data.get('province_code'),32), regency_city_code=clean(data.get('regency_city_code'),32),
      geographic_assignments_json=jdump(data.get('geographic_assignments') or []), location_text=clean(data.get('location_text'),3000), potential_issue_category=clean(data.get('potential_issue_category'),255), analyst_notes=clean(data.get('analyst_notes'),5000),
      evidence_state=clean(data.get('evidence_state') or 'UNVERIFIED',32), evidence_type=clean(data.get('evidence_type') or 'OBSERVED',32), verification_status=clean(data.get('verification_status') or 'UNVERIFIED',32),
      review_status=clean(data.get('review_status') or 'Pending Review',128), priority=clean(data.get('priority') or 'Medium',64), duplicate_of=str(dupe.id) if dupe else '',
      ai_suggestions_json='{}', proposed_geography_json=jdump(data.get('proposed_geography') or {}), ai_geography_json=jdump(data.get('ai_review',{}).get('geography') or data.get('ai_geography') or {})
    )
    proposed=data.get('ai_suggestions') or data.get('ai_review',{}).get('suggestions') or {}
    if proposed:
        proposed=dict(proposed)
        decisions=data.get('ai_review',{}).get('decisions') or {}
        if decisions: proposed['_decisions']=decisions
        run_id=(data.get('ai_review',{}).get('generation') or {}).get('triage_run_id')
        if run_id: proposed['_triage_run_id']=run_id
        item.ai_suggestions_json=jdump(proposed)
    db.add(item); db.commit(); db.refresh(item)
    run_id=(data.get('ai_review',{}).get('generation') or {}).get('triage_run_id')
    if run_id:
        gen=db.query(TriageGeneration).filter(TriageGeneration.triage_run_id==run_id).first()
        if gen and gen.intelligence_item_id is None: gen.intelligence_item_id=item.id; db.commit()
    audit(db,p,'IntelligenceItem',item.id,'CREATED',{'intelligence_id':{'new':item.intelligence_id},'source_url':{'new':item.source_url},'jurisdiction':{'new':{'type':item.jurisdiction_type,'province':item.province,'regency_city':item.regency_city}}})
    return item

def list_intelligence(db,p): return [x for x in db.query(IntelligenceItem).order_by(IntelligenceItem.created_at.desc()).limit(500).all() if allowed(p,x)]

def intelligence_action(db,p,action,data,id=None):
    if action=='runtimeStatus': return {'build_contract':'BAWASLU_STANDALONE_V0_1','function':'intelligence','triage_contract_version':3,'intake_contract_version':'INTAKE_V3_HARDENED_1','server_timestamp':now()}
    if p.get('status')!='Active': raise PermissionError('BAWASLU account access is inactive')
    if action=='list':
        if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
        return {'items':[{**intelligence(x),'geographic_mismatch':geography_mismatch(x)} for x in list_intelligence(db,p)]}
    if action=='activity':
        visible={str(x.id) for x in list_intelligence(db,p)}
        ev=db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(100).all()
        return {'events':[audit_event(x) for x in ev if x.subject_type!='SecurityAccess' and x.subject_id in visible][:10]}
    if action=='retrieve':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        url=clean(data.get('url'),2000); parsed=urlparse(url)
        if parsed.scheme not in ('http','https') or not parsed.netloc: raise ValueError('Public HTTP(S) URL required')
        return {'source_url':url,'source_name':parsed.hostname.removeprefix('www.') if parsed.hostname else '','platform':'Web','title':'','original_content':'','retrieval_status':'URL_ACCEPTED_CONTENT_NOT_FETCHED','requires_manual_content':True}
    if action=='resolveSourceIdentity':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        identity,observed=source_identity(db,data); return {'source_identity':identity,'observed_publisher_handle':observed}
    if action=='create': return {'item':intelligence(create_intelligence(db,p,data))}
    if action=='actorPicture':
        actor_id=str(data.get('actor_id',''))
        rows=[]
        for x in list_intelligence(db,p):
            rels=loads(x.entity_relationships_json,[])
            if x.watchlist_id==actor_id or any(str(r.get('entity_id'))==actor_id and r.get('review_status')=='HUMAN_CONFIRMED' for r in rels): rows.append(intelligence(x))
        return {'records':rows[:100]}
    item=get_item(db,id)
    if not item or not allowed(p,item): raise PermissionError('Access denied')
    if action=='get':
        files=db.query(EvidenceFile).filter(EvidenceFile.intelligence_item_id==item.id).all(); ev=db.query(AuditEvent).filter(AuditEvent.subject_id==str(item.id)).order_by(AuditEvent.id.desc()).limit(100).all()
        allv=list_intelligence(db,p); linked=[x for x in allv if x.id!=item.id and (str(x.id)==item.duplicate_of or x.duplicate_of==str(item.id) or str(x.id)==item.merged_into or x.merged_into==str(item.id))][:20]
        gen=None; sug=loads(item.ai_suggestions_json,{})
        if sug.get('_triage_run_id'):
            g=db.query(TriageGeneration).filter(TriageGeneration.triage_run_id==sug['_triage_run_id']).first()
            if g: gen={'triage_run_id':g.triage_run_id,'triage_schema_version':g.triage_schema_version,'generator':g.generator,'generator_version':g.generator_version,'service_action':g.service_action,'generated_at':g.generated_at,'proposal_field_names':loads(g.proposal_field_names_json,[])}
        return {'item':{**intelligence(item),'geographic_mismatch':geography_mismatch(item)},'generation':gen,'files':[evidence_file(x) for x in files],'events':[audit_event(x) for x in ev],'related':[intelligence(x) for x in linked],'comparison':intelligence(linked[0]) if linked else None}
    if action=='confirmJurisdiction':
        if not has(p,'human_validation') and not has(p,'edit_intelligence'): raise PermissionError('Not permitted')
        item.jurisdiction_type=clean(data.get('jurisdiction_type') or item.jurisdiction_type,32); item.province=clean(data.get('province') or item.province,128); item.regency_city=clean(data.get('regency_city') or item.regency_city,128); item.province_code=clean(data.get('province_code') or item.province_code,32); item.regency_city_code=clean(data.get('regency_city_code') or item.regency_city_code,32); item.jurisdiction_confirmed=True; item.jurisdiction_confirmed_by=p['name']; item.jurisdiction_confirmed_at=now(); item.jurisdiction_source='HUMAN_CONFIRMATION'; item.updated_at=datetime.utcnow(); db.commit(); audit(db,p,'IntelligenceItem',item.id,'JURISDICTION_CONFIRMED',{'province':{'new':item.province},'regency_city':{'new':item.regency_city}}); return {'ok':True}
    if action=='reviewGeographicMismatch':
        if not has(p,'human_validation'): raise PermissionError('Reviewer permission required')
        decision=clean(data.get('decision'),80); reason=clean(data.get('reason'),1000)
        if decision not in ('KEEP_CONFIRMED_JURISDICTION','CHANGE_JURISDICTION'): raise ValueError('Invalid geographic mismatch decision')
        before={'province':item.province,'regency_city':item.regency_city}
        if decision=='CHANGE_JURISDICTION':
            item.province=clean(data.get('province') or data.get('proposed',{}).get('province'),128); item.regency_city=clean(data.get('regency_city') or data.get('proposed',{}).get('regency_city'),128)
        item.geographic_mismatch_review_json=jdump({'decision':decision,'reason':reason,'reviewed_by':p['name'],'reviewed_at':now(),'previous':before}); db.commit(); audit(db,p,'IntelligenceItem',item.id,'GEOGRAPHIC_MISMATCH_REVIEWED',{'decision':{'new':decision},'reason':{'new':reason}}); return {'ok':True}
    if action=='update':
        if not has(p,'edit_intelligence'): raise PermissionError('Not permitted')
        fields=['title','english_translation','source_name','platform','author','publication_datetime','analyst_notes','reason','priority','location_text','assigned_reviewer','evidence_type']
        changes={}
        for k in fields:
            if k in data:
                if k=='assigned_reviewer' and not has(p,'human_validation'): continue
                v=clean(data[k],20000 if k=='english_translation' else 3000); old=getattr(item,k); setattr(item,k,v); changes[k]={'previous':old,'new':v}
        for k,col in [('related_entities','related_entities_json'),('related_topics','related_topics_json')]:
            if k in data: old=loads(getattr(item,col),[]); nv=(data[k] or [])[:20]; setattr(item,col,jdump(nv)); changes[k]={'previous':old,'new':nv}
        item.updated_at=datetime.utcnow(); db.commit();
        if changes: audit(db,p,'IntelligenceItem',item.id,'EDITED',changes)
        return {'ok':True}
    if action=='verifyEvidence':
        if not has(p,'verify_evidence'): raise PermissionError('Evidence verification permission required')
        if item.verification_status=='HUMAN_VERIFIED': raise ValueError('Evidence already human verified')
        item.verification_status='HUMAN_VERIFIED'; item.evidence_state='VERIFIED'; db.commit(); audit(db,p,'IntelligenceItem',item.id,'EVIDENCE_VERIFIED',{'verification_status':{'new':'HUMAN_VERIFIED'},'evidence_state':{'new':'VERIFIED'}}); return {'ok':True}
    if action=='review':
        if not has(p,'human_validation'): raise PermissionError('Reviewer permission required')
        decision=clean(data.get('decision'),128)
        if decision not in ['Validated as Relevant Intelligence','Request More Information','Not Relevant','Escalate for Further Review']: raise ValueError('Invalid review decision')
        if decision=='Validated as Relevant Intelligence' and geography_mismatch(item).get('status')=='pending': raise ValueError('GEOGRAPHIC MISMATCH — REVIEW REQUIRED before final validation')
        item.review_status=decision; item.review_notes=clean(data.get('review_notes'),5000); item.assigned_reviewer=p['name']; item.validated_at=now(); db.commit(); audit(db,p,'IntelligenceItem',item.id,'REVIEWED',{'review_status':{'new':decision},'review_notes':{'new':item.review_notes}}); return {'ok':True}
    if action=='duplicate':
        if not has(p,'human_validation'): raise PermissionError('Reviewer permission required')
        decision=clean(data.get('decision'),64)
        if decision not in ('Merge','Keep Separate'): raise ValueError('Invalid duplicate decision')
        item.duplicate_resolution=decision
        if decision=='Merge': item.merged_into=item.duplicate_of; item.review_status='Merged with Related Intelligence'
        db.commit(); audit(db,p,'IntelligenceItem',item.id,'DUPLICATE_REVIEWED',{'duplicate_resolution':{'new':decision},'merged_into':{'new':item.merged_into}}); return {'ok':True}
    if action=='attach':
        if not has(p,'upload_evidence'): raise PermissionError('Not permitted')
        uri=clean(data.get('file_uri'),2000); filename=clean(data.get('original_filename'),500); ext=filename.rsplit('.',1)[-1].lower() if '.' in filename else ''
        if not uri or not filename or ext not in {'pdf','docx','xlsx','csv','png','jpg','jpeg','webp'}: raise ValueError('Approved file required')
        f=EvidenceFile(intelligence_item_id=item.id,file_uri=uri,original_filename=filename,file_type=ext,uploaded_by=p['name'],uploaded_at=now(),related_entity=clean(data.get('related_entity'),255),related_location=item.regency_city or item.province,description=clean(data.get('description'),5000),evidence_state=item.evidence_state); db.add(f); db.commit(); db.refresh(f); audit(db,p,'IntelligenceItem',item.id,'EVIDENCE_ADDED',{'filename':{'new':filename},'file_id':{'new':str(f.id)}}); return {'file':evidence_file(f)}
    if action=='fileLink':
        f=db.get(EvidenceFile,int(data.get('file_id'))) if str(data.get('file_id','')).isdigit() else None
        if not f or f.intelligence_item_id!=item.id: raise ValueError('Not found')
        return {'url':f.file_uri}
    if action=='runTriage':
        if not has(p,'review_ai_suggestions'): raise PermissionError('Not permitted')
        run_id=str(uuid.uuid4()); source_fp=hashlib.sha256((item.original_content+'|'+item.source_url).encode()).hexdigest(); proposal={'_version':3,'_triage_run_id':run_id,'summary':item.ai_summary or '','analysis':item.ai_analysis or '','confidence':item.confidence or '','priority':item.priority or 'Medium'}; prop_fp=hashlib.sha256(jdump(proposal).encode()).hexdigest(); g=TriageGeneration(triage_run_id=run_id,intelligence_item_id=item.id,initiated_by_id=p['id'],source_fingerprint=source_fp,proposal_fingerprint=prop_fp,triage_schema_version=3,generator='standalone-local',generator_version='v0.1',service_action='runTriage',generated_at=now(),validation_outcome='GENERATED',proposal_field_names_json=jdump(list(proposal))); db.add(g); item.ai_suggestions_json=jdump(proposal); db.commit(); audit(db,p,'IntelligenceItem',item.id,'AI_TRIAGE_GENERATED',{'triage_run_id':{'new':run_id}}); return {'suggestions':proposal,'generation':{'triage_run_id':run_id,'triage_schema_version':3,'generator':'standalone-local','generator_version':'v0.1','service_action':'runTriage','generated_at':g.generated_at,'proposal_field_names':list(proposal)},'geography':loads(item.ai_geography_json,{}),'watchlist_match':None}
    if action=='triageDecision':
        if not has(p,'review_ai_suggestions'): raise PermissionError('Not permitted')
        key=clean(data.get('key'),100); status=clean(data.get('status'),64); reason=clean(data.get('reason'),500); value=data.get('value')
        if status not in ('Human Accepted','Human Modified','Human Rejected'): raise ValueError('Invalid human decision')
        if status=='Human Rejected' and len(reason)<5: raise ValueError('A short human rejection reason is required')
        sug=loads(item.ai_suggestions_json,{}); decisions=sug.setdefault('_decisions',{}); decisions[key]={'status':status,'value':value,'reason':reason,'reviewer':p['name'],'reviewer_id':p['id'],'decided_at':now()}; item.ai_suggestions_json=jdump(sug); db.commit(); audit(db,p,'IntelligenceItem',item.id,'AI_SUGGESTION_DECIDED',{key:{'new':decisions[key]}}); return {'ok':True}
    if action=='linkWatchlist':
        if not has(p,'review_ai_suggestions'): raise PermissionError('Not permitted')
        wid=str(data.get('watchlist_id','')); w=db.get(WatchlistItem,int(wid)) if wid.isdigit() else None
        if not w or not allowed(p,w): raise ValueError('Watchlist item unavailable')
        decision=data.get('decision')
        if decision=='Link': item.watchlist_id=wid; ents=loads(item.related_entities_json,[]); item.related_entities_json=jdump(list(dict.fromkeys(ents+[w.name]))[:20])
        elif decision!='Reject': raise ValueError('Invalid decision')
        db.commit(); audit(db,p,'IntelligenceItem',item.id,'WATCHLIST_MATCH_REVIEWED',{'watchlist_id':{'new':wid if decision=='Link' else None},'decision':{'new':decision}}); return {'ok':True}
    if action=='recoverSource': return {'ok':True,'item':intelligence(item),'message':'Standalone v0.1 keeps source recovery human-controlled; no external fetch was performed.'}
    raise ValueError('Unknown action')
