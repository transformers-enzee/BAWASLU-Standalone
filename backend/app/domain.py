import hashlib, json, re, uuid
from difflib import SequenceMatcher
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlalchemy.orm import Session
from .models import *
from .serializers import *
from .access import has, allowed, audit
from .source_retrieval import fetch_public_source, clean_article_text, _language_detection, language_label
from .geography import normalize_jurisdiction
from .openai_triage import openai_triage_configured, generate_openai_triage, OpenAITriageError

def now(): return datetime.now(timezone.utc).isoformat()
def jdump(v): return json.dumps(v,ensure_ascii=False)
def clean(v,n=5000): return (v.strip()[:n] if isinstance(v,str) else '')

TRIAGE_REVIEW_FIELDS=[
 'summary','english_translation','entity','actor_evidence','content_type','activity','location','topic','narrative','relationships','inference','actors',
 'location_signal','topics','inferences','screening_evidence_basis','screening_confidence','supervision_signal','signal_reason','check_next','priority',
 'evidence_type','evidence_gaps','issue_category','suggested_evidence_state','analysis','reasoning','watchlist_match'
]
TRIAGE_DECISION_STATUSES={'Human Accepted','Human Modified','Human Rejected'}
V3_TRIAGE_SCALAR_FIELDS=['summary','english_translation','content_type','supervision_signal','signal_reason','screening_confidence','priority','evidence_type','confidence']
V3_TRIAGE_STRUCTURED_FIELDS=['activity','actors','location_signal','narrative','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis']
V3_TRIAGE_ALLOWED=set(V3_TRIAGE_SCALAR_FIELDS+V3_TRIAGE_STRUCTURED_FIELDS+['source_facts','_version','_triage_run_id','_decisions','watchlist_match'])

def _local_v3_triage(item,run_id,source_text=None):
    source_text=re.sub(r'\s+',' ',source_text if source_text is not None else (item.original_content or '')).strip()
    if not source_text:
        raise ValueError('Original source content is required before AI Triage can be generated')
    source_facts=source_text[:4000]
    summary=clean(item.ai_summary or item.title or source_facts,1200)
    priority=item.priority if item.priority in ('Critical','High','Medium','Low') else 'Medium'
    evidence_type=item.evidence_type if item.evidence_type in ('OBSERVED','INFERRED') else 'OBSERVED'
    return {
      '_version':3,
      '_triage_run_id':run_id,
      'source_facts':source_facts,
      'summary':summary,
      'english_translation':clean(item.english_translation,4000),
      'content_type':'',
      'activity':'',
      'actors':'',
      'location_signal':'',
      'narrative':'',
      'relationships':'',
      'topics':'',
      'evidence_gaps':'',
      'inferences':'',
      'check_next':'',
      'screening_evidence_basis':'',
      'supervision_signal':'NO SIGNAL IDENTIFIED',
      'signal_reason':'',
      'screening_confidence':'LOW',
      'priority':priority,
      'evidence_type':evidence_type,
      'confidence':'LOW'
    }

def _valid_v3_proposal(value):
    if not isinstance(value,dict) or value.get('_version')!=3: return False
    if any(k not in V3_TRIAGE_ALLOWED for k in value): return False
    if any(not isinstance(value.get(k,''),str) for k in V3_TRIAGE_SCALAR_FIELDS+V3_TRIAGE_STRUCTURED_FIELDS+['source_facts']): return False
    if not value.get('summary','').strip() or not value.get('confidence','').strip() or not value.get('screening_confidence','').strip(): return False
    if value.get('supervision_signal') not in ('NO SIGNAL IDENTIFIED','MONITOR','REVIEW RECOMMENDED','POTENTIAL REGULATORY ISSUE'): return False
    if value.get('evidence_type') not in ('OBSERVED','INFERRED'): return False
    if value.get('priority') not in ('Critical','High','Medium','Low'): return False
    for key in V3_TRIAGE_STRUCTURED_FIELDS:
        raw=value.get(key,'')
        if not raw: continue
        try: parsed=json.loads(raw)
        except Exception: return False
        if key in ('actors','relationships','topics','evidence_gaps','inferences','check_next','screening_evidence_basis') and not isinstance(parsed,list): return False
        if key in ('activity','location_signal','narrative') and not isinstance(parsed,dict): return False
    if value.get('supervision_signal')!='NO SIGNAL IDENTIFIED':
        if not value.get('signal_reason','').strip() or not value.get('check_next') or not value.get('screening_evidence_basis'): return False
    return True

def _triage_reviewable(item):
    suggestions=loads(item.ai_suggestions_json,{}) or {}
    if item.source_type=='REGISTERED_OWNED_CHANNEL':
        owned=loads(item.owned_channel_json,{}) or {}
        match=suggestions.get('watchlist_match') or {}
        if match.get('id') and str(match.get('id'))==str(owned.get('candidate_id') or ''):
            suggestions=dict(suggestions); suggestions['watchlist_match']=None
    fields=[]
    for key in TRIAGE_REVIEW_FIELDS:
        value=suggestions.get(key)
        if key=='watchlist_match':
            if isinstance(value,dict) and value.get('id'): fields.append(key)
        elif isinstance(value,str) and value.strip():
            fields.append(key)
    return suggestions,fields

def triage_review_status(item):
    suggestions,fields=_triage_reviewable(item)
    decisions=suggestions.get('_decisions') or {}
    valid={k:v for k,v in decisions.items() if isinstance(v,dict) and v.get('status') in TRIAGE_DECISION_STATUSES}
    reviewed=[k for k in fields if k in valid]
    legacy=not fields and bool(decisions)
    generated=bool(fields) or legacy
    if not generated:
        state='NOT GENERATED'
    elif legacy:
        state='IN REVIEW'
    elif not reviewed:
        state='NOT STARTED'
    elif len(reviewed)==len(fields):
        state='REVIEW COMPLETE'
    else:
        state='IN REVIEW'
    return {
      'generated':generated,'state':state,'reviewed':len(reviewed),'total':len(fields),'legacy':legacy,
      'pending_keys':[k for k in fields if k not in valid],'reviewed_keys':reviewed
    }

def _approved_triage_value(key,value):
    if key in V3_TRIAGE_STRUCTURED_FIELDS and isinstance(value,str) and value.strip():
        try: return json.loads(value)
        except Exception: return value
    return value

def human_approved_triage(item):
    suggestions,reviewable=_triage_reviewable(item)
    decisions=suggestions.get('_decisions') or {}
    values={}
    provenance={}
    rejected=[]
    field_states={}
    for key in reviewable:
        decision=decisions.get(key) if isinstance(decisions.get(key),dict) else {}
        status=decision.get('status')
        base={
          'reviewer':decision.get('reviewer') or '',
          'reviewer_id':decision.get('reviewer_id') or '',
          'decided_at':decision.get('decided_at') or '',
          'reason':decision.get('reason') or ''
        }
        if status=='Human Rejected':
            rejected.append(key)
            field_states[key]={**base,'state':'REJECTED','decision':status,'source':'HUMAN_REJECTED_AI_SUGGESTION'}
            continue
        if status in ('Human Accepted','Human Modified'):
            raw=decision.get('value') if status=='Human Modified' else suggestions.get(key)
            if raw is not None and (not isinstance(raw,str) or raw.strip()):
                values[key]=_approved_triage_value(key,raw)
                provenance[key]={
                  'decision':status,
                  'reviewer':base['reviewer'],
                  'reviewer_id':base['reviewer_id'],
                  'decided_at':base['decided_at'],
                  'source':'HUMAN_MODIFIED_AI_SUGGESTION' if status=='Human Modified' else 'HUMAN_ACCEPTED_AI_SUGGESTION'
                }
                field_states[key]={**base,'state':'APPROVED','decision':status,'source':provenance[key]['source']}
                continue
        field_states[key]={**base,'state':'PENDING','decision':''}
    return {
      'values':values,
      'provenance':provenance,
      'field_states':field_states,
      'reviewable_fields':sorted(reviewable),
      'rejected_fields':sorted(rejected),
      'approved_count':len(values),
      'review_state':triage_review_status(item).get('state')
    }

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

TRACKING_QUERY_KEYS={'utm_source','utm_medium','utm_campaign','utm_term','utm_content','utm_id','gclid','fbclid','mc_cid','mc_eid'}

def _norm_text(value):
    return re.sub(r'[^a-z0-9]+',' ',str(value or '').lower()).strip()

def _canonical_url(value):
    raw=clean(value,2000)
    if not raw: return ''
    try:
        p=urlparse(raw)
        host=(p.hostname or '').lower().removeprefix('www.')
        if not host: return raw.rstrip('/').lower()
        port=f':{p.port}' if p.port and p.port not in (80,443) else ''
        path=re.sub(r'/+','/',p.path or '/').rstrip('/') or '/'
        query=urlencode([(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if k.lower() not in TRACKING_QUERY_KEYS])
        return urlunparse(((p.scheme or 'https').lower(),host+port,path,'',query,''))
    except Exception:
        return raw.rstrip('/').lower()

def _token_set(value,limit=600):
    tokens=_norm_text(value).split()
    return set(tokens[:limit])

def _jaccard(a,b):
    if len(a)<4 or len(b)<4: return 0.0
    union=a|b
    return len(a&b)/len(union) if union else 0.0

def duplicate_similarity(data, candidate):
    incoming={
      'source_url':data.get('source_url') if isinstance(data,dict) else getattr(data,'source_url',''),
      'title':data.get('title') if isinstance(data,dict) else getattr(data,'title',''),
      'original_content':data.get('original_content') if isinstance(data,dict) else getattr(data,'original_content',''),
      'source_name':data.get('source_name') if isinstance(data,dict) else getattr(data,'source_name',''),
      'author':data.get('author') if isinstance(data,dict) else getattr(data,'author',''),
      'platform':data.get('platform') if isinstance(data,dict) else getattr(data,'platform',''),
      'publication_date':data.get('publication_date') if isinstance(data,dict) else getattr(data,'publication_date',''),
    }
    existing={
      'source_url':getattr(candidate,'source_url',''),
      'title':getattr(candidate,'title',''),
      'original_content':getattr(candidate,'original_content',''),
      'source_name':getattr(candidate,'source_name',''),
      'author':getattr(candidate,'author',''),
      'platform':getattr(candidate,'platform',''),
      'publication_date':getattr(candidate,'publication_date',''),
    }
    url_a,url_b=_canonical_url(incoming['source_url']),_canonical_url(existing['source_url'])
    if url_a and url_b and url_a==url_b:
        return {'score':1.0,'basis':['Same source URL'],'signals':{'url_exact':True,'title_similarity':1.0 if _norm_text(incoming['title'])==_norm_text(existing['title']) and incoming['title'] else 0.0,'content_similarity':0.0}}

    title_a,title_b=_norm_text(incoming['title']),_norm_text(existing['title'])
    title_similarity=SequenceMatcher(None,title_a,title_b).ratio() if title_a and title_b else 0.0
    content_similarity=_jaccard(_token_set(incoming['original_content']),_token_set(existing['original_content']))
    source_a=_norm_text(incoming['source_name'] or incoming['author'])
    source_b=_norm_text(existing['source_name'] or existing['author'])
    same_source=bool(source_a and source_b and source_a==source_b)
    same_date=bool(incoming['publication_date'] and existing['publication_date'] and incoming['publication_date']==existing['publication_date'])
    same_platform=bool(_norm_text(incoming['platform']) and _norm_text(incoming['platform'])==_norm_text(existing['platform']))

    score=(0.55*title_similarity)+(0.30*content_similarity)+(0.08 if same_source else 0)+(0.05 if same_date else 0)+(0.02 if same_platform else 0)
    exact_title=bool(title_a and title_a==title_b)
    if exact_title: score=max(score,0.94)

    basis=[]
    if exact_title: basis.append('Same normalized headline')
    elif title_similarity>=0.90: basis.append('Very similar headline')
    elif title_similarity>=0.82: basis.append('Similar headline')
    if content_similarity>=0.70: basis.append('Highly overlapping source text')
    elif content_similarity>=0.45: basis.append('Overlapping source text')
    if same_source: basis.append('Same source / publisher')
    if same_date: basis.append('Same publication date')
    if same_platform: basis.append('Same platform')

    return {
      'score':round(min(score,1.0),3),
      'basis':basis,
      'signals':{
        'url_exact':False,
        'title_similarity':round(title_similarity,3),
        'content_similarity':round(content_similarity,3),
        'same_source':same_source,
        'same_date':same_date,
        'same_platform':same_platform,
      }
    }

def duplicate_candidate(db, data):
    candidates=db.query(IntelligenceItem).order_by(IntelligenceItem.id.desc()).limit(250).all()
    best=None
    for candidate in candidates:
        match=duplicate_similarity(data,candidate)
        title_sim=match['signals'].get('title_similarity',0)
        content_sim=match['signals'].get('content_similarity',0)
        support=match['signals'].get('same_source') or match['signals'].get('same_date') or content_sim>=0.45
        qualifies=match['score']>=0.78 and (match['signals'].get('url_exact') or title_sim>=0.82 and support)
        if _norm_text(data.get('title')) and _norm_text(data.get('title'))==_norm_text(candidate.title):
            qualifies=True
        if qualifies and (best is None or match['score']>best[1]['score']):
            best=(candidate,match)
    return best if best else (None,None)

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

def source_language_resolution(item):
    metadata=loads(item.provider_source_metadata_json,{}) or {}
    selection_source=str(metadata.get('language_selection_source') or '').upper()
    recorded=clean(item.original_language_code,20).lower()
    detection=_language_detection(item.original_content or item.title or '',recorded)
    detected=clean(detection.get('code'),20).lower()
    if selection_source=='ANALYST' and recorded:
        code=recorded; method='ANALYST_CONFIRMED'; confidence='HUMAN'
    elif detected and detection.get('confidence') in ('HIGH','MEDIUM'):
        code=detected; method=detection.get('method') or 'SYSTEM_DETECTED'; confidence=detection.get('confidence') or 'MEDIUM'
    else:
        code=recorded or detected; method='RECORDED_FALLBACK' if recorded else detection.get('method') or 'UNRESOLVED'; confidence=detection.get('confidence') or 'LOW'
    return {'code':code,'label':language_label(code) if code else 'Undetermined','confidence':confidence,'method':method,'recorded_code':recorded,'detected_code':detected,'mismatch':bool(recorded and detected and recorded!=detected),'selection_source':selection_source or 'SYSTEM_OR_LEGACY','detection':detection}

def triage_source_view(item):
    cleaned,meta=clean_article_text(item.original_content or '')
    return {'text':cleaned,'cleaning':meta,'language':source_language_resolution(item)}

def _jurisdiction_payload(item):
    return {
      'jurisdiction_type':item.jurisdiction_type or 'Unresolved',
      'province':item.province or '',
      'province_code':item.province_code or '',
      'regency_city':item.regency_city or '',
      'regency_city_code':item.regency_city_code or '',
      'geographic_assignments':loads(item.geographic_assignments_json,[])
    }

def _proposed_jurisdiction(proposed):
    proposed=dict(proposed or {})
    if not proposed.get('jurisdiction_type'):
        if proposed.get('geographic_assignments'):
            proposed['jurisdiction_type']='Multi-Region'
        elif proposed.get('regency_city') or proposed.get('regency_city_name') or proposed.get('regency_city_code'):
            proposed['jurisdiction_type']='Regency / City'
        elif proposed.get('province') or proposed.get('province_name') or proposed.get('province_code'):
            proposed['jurisdiction_type']='Province'
        else:
            proposed['jurisdiction_type']='Unresolved'
    if not proposed.get('province') and proposed.get('province_name'):
        proposed['province']=proposed.get('province_name')
    if not proposed.get('regency_city') and proposed.get('regency_city_name'):
        proposed['regency_city']=proposed.get('regency_city_name')
    try:
        return normalize_jurisdiction(proposed,require_valid=False)
    except Exception:
        return {'jurisdiction_type':'Unresolved','province':'','province_code':'','regency_city':'','regency_city_code':'','geographic_assignments':[]}

def _jurisdiction_signature(geo):
    kind=geo.get('jurisdiction_type') or 'Unresolved'
    if kind=='Multi-Region':
        rows=geo.get('geographic_assignments') or []
        return (kind,tuple(sorted((x.get('province_code') or _norm_text(x.get('province')),x.get('regency_city_code') or _norm_text(x.get('regency_city'))) for x in rows)))
    return (kind,geo.get('province_code') or _norm_text(geo.get('province')),geo.get('regency_city_code') or _norm_text(geo.get('regency_city')))

def geography_mismatch(item):
    proposed_raw=loads(item.proposed_geography_json,{}) or loads(item.ai_geography_json,{})
    review=loads(item.geographic_mismatch_review_json,{})
    if not proposed_raw or not item.jurisdiction_confirmed:
        return {'status':'resolved',**review,'proposed':proposed_raw} if review.get('decision') else {'status':'none'}

    confirmed=normalize_jurisdiction(_jurisdiction_payload(item),require_valid=False)
    proposed=_proposed_jurisdiction(proposed_raw)
    basis=proposed_raw.get('supporting_text') or proposed_raw.get('evidence') or ''
    if proposed.get('jurisdiction_type')=='Unresolved':
        return {'status':'resolved',**review,'proposed':proposed_raw,'confirmed':confirmed} if review.get('decision') else {'status':'none'}

    mismatch=_jurisdiction_signature(confirmed)!=_jurisdiction_signature(proposed)
    fp=hashlib.sha256(jdump({'item_id':str(item.id),'confirmed':confirmed,'proposed':proposed,'basis':basis}).encode()).hexdigest()

    if not mismatch:
        if review.get('decision'):
            return {'status':'resolved',**review,'proposed':proposed_raw,'confirmed':confirmed,'supporting_text':basis}
        return {'status':'none'}

    if review.get('decision') and review.get('fingerprint')==fp:
        return {'status':'resolved',**review,'proposed':proposed_raw,'confirmed':confirmed,'supporting_text':basis}

    result={'status':'pending','fingerprint':fp,'proposed':proposed_raw,'normalized_proposed':proposed,'confirmed':confirmed,'supporting_text':basis}
    if review.get('decision'):
        result['previous_review']=review
        result['review_reopened']=True
    return result

def create_intelligence(db,p,data):
    if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
    dupe,dupe_match=duplicate_candidate(db,data)
    identity, observed=source_identity(db,data)
    geo=normalize_jurisdiction(data,require_valid=bool(data.get('confirm_jurisdiction') or data.get('jurisdiction_confirmed')))
    source_text=clean(data.get('original_content') or data.get('description'),20000)
    provider_meta=dict(data.get('provider_source_metadata') or {})
    selected_language=clean(data.get('original_language_code'),20).lower()
    if str(provider_meta.get('language_selection_source') or '').upper()!='ANALYST':
        detected_language=_language_detection(source_text,selected_language)
        if detected_language.get('code') and detected_language.get('confidence') in ('HIGH','MEDIUM'):
            selected_language=detected_language['code']
        provider_meta['language_detection']=detected_language
        provider_meta.setdefault('language_selection_source','SYSTEM_DETECTED')
    item=IntelligenceItem(
      intelligence_id=next_intelligence_id(db), title=clean(data.get('title'),3000), original_content=source_text,
      original_language=language_label(selected_language) if selected_language else clean(data.get('original_language'),100), original_language_code=selected_language, english_translation=clean(data.get('english_translation'),20000),
      source_type=clean(data.get('source_type'),64), ingestion_method=clean(data.get('ingestion_method') or ({'MANUAL_LINK':'MANUAL_URL','FILE_UPLOAD':'FILE_UPLOAD'}.get(data.get('source_type'),'MANUAL_ENTRY')),64),
      observed_publisher_handle=clean(data.get('observed_publisher_handle') or observed,255), provider_source_metadata_json=jdump(provider_meta), source_identity_json=jdump(data.get('source_identity') or identity),
      entity_relationships_json=jdump(data.get('entity_relationships') or []), source_id=clean(data.get('source_id'),255), source_url=clean(data.get('source_url'),2000), source_name=clean(data.get('source_name'),255),
      platform=clean(data.get('platform'),100), author=clean(data.get('author') or observed,255), publication_datetime=clean(data.get('publication_datetime'),64), publication_date=clean(data.get('publication_date'),32),
      publication_time_precision=clean(data.get('publication_time_precision') or 'UNKNOWN',32), collection_datetime=clean(data.get('collection_datetime') or now(),64), owned_channel_json=jdump(data.get('owned_channel') or {}),
      related_entities_json=jdump((data.get('related_entities') or [])[:20]), related_topics_json=jdump((data.get('related_topics') or [])[:20]), jurisdiction_type=geo['jurisdiction_type'],
      jurisdiction_confirmed=bool(data.get('confirm_jurisdiction') or data.get('jurisdiction_confirmed')), jurisdiction_confirmed_by=p['name'] if data.get('confirm_jurisdiction') else clean(data.get('jurisdiction_confirmed_by'),255),
      jurisdiction_confirmed_at=now() if data.get('confirm_jurisdiction') else clean(data.get('jurisdiction_confirmed_at'),64), jurisdiction_source=clean(data.get('jurisdiction_source') or ('HUMAN_INTAKE' if data.get('confirm_jurisdiction') else ''),128),
      province=geo['province'], regency_city=geo['regency_city'], province_code=geo['province_code'], regency_city_code=geo['regency_city_code'],
      geographic_assignments_json=jdump(geo['geographic_assignments']), location_text=clean(data.get('location_text'),3000), potential_issue_category=clean(data.get('potential_issue_category'),255), analyst_notes=clean(data.get('analyst_notes'),5000),
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
    audit(db,p,'IntelligenceItem',item.id,'CREATED',{'intelligence_id':{'new':item.intelligence_id},'source_url':{'new':item.source_url},'jurisdiction':{'new':{'type':item.jurisdiction_type,'province':item.province,'regency_city':item.regency_city}},'duplicate_candidate':{'new':{'id':str(dupe.id),'intelligence_id':dupe.intelligence_id,'score':dupe_match['score'],'basis':dupe_match['basis']} if dupe else None}})
    return item

SOURCE_RECOVERY_FIELDS={
 'title':3000,
 'original_content':20000,
 'source_name':255,
 'platform':100,
 'author':255,
 'original_language_code':20,
}

def _missing_source_value(item,field):
    value=getattr(item,field,'')
    return value is None or (isinstance(value,str) and not value.strip())

def apply_source_recovery(item,retrieved):
    changes={}
    recovered=[]
    for field,max_len in SOURCE_RECOVERY_FIELDS.items():
        value=clean(retrieved.get(field),max_len)
        if value and _missing_source_value(item,field):
            old=getattr(item,field,'')
            setattr(item,field,value)
            changes[field]={'previous':old,'new':value}
            recovered.append(field)

    incoming_date=clean(retrieved.get('publication_date'),32)
    incoming_precision=clean(retrieved.get('publication_time_precision'),32)
    incoming_time=clean(retrieved.get('publication_time'),32)
    if incoming_precision=='DATE_ONLY':
        incoming_precision='TIME_UNKNOWN'
    if incoming_precision=='EXACT' and not incoming_time:
        incoming_precision='TIME_UNKNOWN'

    if incoming_date and _missing_source_value(item,'publication_date'):
        old=item.publication_date
        item.publication_date=incoming_date
        changes['publication_date']={'previous':old,'new':incoming_date}
        recovered.append('publication_date')

    if incoming_precision and (not item.publication_time_precision or item.publication_time_precision=='UNKNOWN'):
        old=item.publication_time_precision
        item.publication_time_precision=incoming_precision
        changes['publication_time_precision']={'previous':old,'new':incoming_precision}
        recovered.append('publication_time_precision')

    if incoming_date and incoming_precision=='EXACT' and incoming_time and _missing_source_value(item,'publication_datetime'):
        combined=f'{incoming_date}T{incoming_time}'
        old=item.publication_datetime
        item.publication_datetime=combined
        changes['publication_datetime']={'previous':old,'new':combined}
        recovered.append('publication_datetime')

    item.updated_at=datetime.utcnow()
    return changes,recovered

def list_intelligence(db,p): return [x for x in db.query(IntelligenceItem).order_by(IntelligenceItem.created_at.desc()).limit(500).all() if allowed(p,x)]

def intelligence_action(db,p,action,data,id=None):
    if action=='runtimeStatus': return {'build_contract':'BAWASLU_STANDALONE_V0_1','function':'intelligence','triage_contract_version':3,'intake_contract_version':'INTAKE_V3_HARDENED_1','server_timestamp':now()}
    if p.get('status')!='Active': raise PermissionError('BAWASLU account access is inactive')
    if action=='list':
        if not has(p,'view_intelligence'): raise PermissionError('Not permitted')
        return {'items':[{**intelligence(x),'geographic_mismatch':geography_mismatch(x),'triage_review':triage_review_status(x),'human_approved_triage':human_approved_triage(x),'language_resolution':source_language_resolution(x)} for x in list_intelligence(db,p)]}
    if action=='activity':
        visible={str(x.id) for x in list_intelligence(db,p)}
        ev=db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(100).all()
        return {'events':[audit_event(x) for x in ev if x.subject_type!='SecurityAccess' and x.subject_id in visible][:10]}
    if action=='retrieve':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        url=clean(data.get('url'),2000)
        result=fetch_public_source(url)
        return result
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
            if g:
                source_view=triage_source_view(item)
                gen={'triage_run_id':g.triage_run_id,'triage_schema_version':g.triage_schema_version,'generator':g.generator,'generator_version':g.generator_version,'service_action':g.service_action,'generated_at':g.generated_at,'validation_outcome':g.validation_outcome,'proposal_field_names':loads(g.proposal_field_names_json,[]),'source_cleaning':source_view['cleaning'],'language_resolution':source_view['language']}
        comparison_item=get_item(db,item.duplicate_of) if item.duplicate_of else None
        if comparison_item and not allowed(p,comparison_item): comparison_item=None
        if not comparison_item and linked: comparison_item=linked[0]
        duplicate_match=duplicate_similarity(item,comparison_item) if comparison_item and item.duplicate_of else None
        return {'item':{**intelligence(item),'geographic_mismatch':geography_mismatch(item),'triage_review':triage_review_status(item),'human_approved_triage':human_approved_triage(item),'language_resolution':source_language_resolution(item)},'generation':gen,'files':[evidence_file(x) for x in files],'events':[audit_event(x) for x in ev],'related':[intelligence(x) for x in linked],'comparison':intelligence(comparison_item) if comparison_item else None,'duplicate_match':duplicate_match}
    if action=='confirmJurisdiction':
        if not has(p,'human_validation') and not has(p,'edit_intelligence'): raise PermissionError('Not permitted')
        geo=normalize_jurisdiction(data,require_valid=True)
        if geo['jurisdiction_type']=='Unresolved': raise ValueError('Unresolved jurisdiction cannot be confirmed')
        before=_jurisdiction_payload(item)
        item.jurisdiction_type=geo['jurisdiction_type']; item.province=geo['province']; item.regency_city=geo['regency_city']; item.province_code=geo['province_code']; item.regency_city_code=geo['regency_city_code']; item.geographic_assignments_json=jdump(geo['geographic_assignments']); item.jurisdiction_confirmed=True; item.jurisdiction_confirmed_by=p['name']; item.jurisdiction_confirmed_at=now(); item.jurisdiction_source='HUMAN_CONFIRMATION'; item.updated_at=datetime.utcnow()
        if _jurisdiction_signature(normalize_jurisdiction(before,require_valid=False))!=_jurisdiction_signature(geo):
            item.geographic_mismatch_review_json='{}'
        db.commit(); audit(db,p,'IntelligenceItem',item.id,'JURISDICTION_CONFIRMED',{'previous':before,'new':geo}); return {'ok':True}
    if action=='reviewGeographicMismatch':
        if not has(p,'human_validation'): raise PermissionError('Reviewer permission required')
        current=geography_mismatch(item)
        if current.get('status')!='pending': raise ValueError('No pending geographic mismatch requires review')
        decision=clean(data.get('decision'),80); reason=clean(data.get('reason'),1000)
        if decision not in ('KEEP_CONFIRMED_JURISDICTION','CHANGE_JURISDICTION'): raise ValueError('Invalid geographic mismatch decision')
        if len(reason)<3: raise ValueError('Analyst note / reason is required')
        before=normalize_jurisdiction(_jurisdiction_payload(item),require_valid=False)
        after=before
        if decision=='CHANGE_JURISDICTION':
            requested=dict(current.get('normalized_proposed') or _proposed_jurisdiction(current.get('proposed') or {}))
            for key in ('jurisdiction_type','province','province_code','regency_city','regency_city_code','geographic_assignments'):
                if key in data and data.get(key) not in (None,'',[]):
                    requested[key]=data.get(key)
            after=normalize_jurisdiction(requested,require_valid=True)
            if after.get('jurisdiction_type')=='Unresolved': raise ValueError('Changed jurisdiction must be resolved')
            item.jurisdiction_type=after['jurisdiction_type']; item.province=after['province']; item.regency_city=after['regency_city']; item.province_code=after['province_code']; item.regency_city_code=after['regency_city_code']; item.geographic_assignments_json=jdump(after['geographic_assignments']); item.jurisdiction_confirmed=True; item.jurisdiction_confirmed_by=p['name']; item.jurisdiction_confirmed_at=now(); item.jurisdiction_source='GEOGRAPHIC_MISMATCH_REVIEW'
        review={'decision':decision,'reason':reason,'reviewed_by':p['name'],'reviewed_at':now(),'fingerprint':current.get('fingerprint'),'previous':before,'resulting_jurisdiction':after,'proposed':current.get('proposed') or {}}
        item.geographic_mismatch_review_json=jdump(review); item.updated_at=datetime.utcnow(); db.commit()
        audit(db,p,'IntelligenceItem',item.id,'GEOGRAPHIC_MISMATCH_REVIEWED',{'decision':{'new':decision},'reason':{'new':reason},'previous_jurisdiction':{'previous':before},'resulting_jurisdiction':{'new':after},'fingerprint':{'new':current.get('fingerprint')}}); return {'ok':True}
    if action=='update':
        if not has(p,'edit_intelligence'): raise PermissionError('Not permitted')
        fields=['title','english_translation','source_name','platform','author','publication_datetime','analyst_notes','reason','priority','location_text','assigned_reviewer','evidence_type','original_language_code']
        changes={}
        for k in fields:
            if k in data:
                if k=='assigned_reviewer' and not has(p,'human_validation'): continue
                v=clean(data[k],20000 if k=='english_translation' else 3000); old=getattr(item,k); setattr(item,k,v); changes[k]={'previous':old,'new':v}
        for k,col in [('related_entities','related_entities_json'),('related_topics','related_topics_json')]:
            if k in data: old=loads(getattr(item,col),[]); nv=(data[k] or [])[:20]; setattr(item,col,jdump(nv)); changes[k]={'previous':old,'new':nv}
        if 'original_language_code' in data:
            metadata=loads(item.provider_source_metadata_json,{}) or {}
            metadata['language_selection_source']='ANALYST'
            metadata['language_selection_code']=item.original_language_code
            item.provider_source_metadata_json=jdump(metadata)
            item.original_language=language_label(item.original_language_code) if item.original_language_code else ''
            changes['language_selection_source']={'new':'ANALYST'}
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
        notes=clean(data.get('review_notes'),5000)
        if decision not in ['Validated as Relevant Intelligence','Request More Information','Not Relevant','Escalate for Further Review']: raise ValueError('Invalid review decision')
        if decision in ['Request More Information','Not Relevant','Escalate for Further Review'] and len(notes)<3:
            raise ValueError('Reviewer notes are required for this decision')
        if decision=='Validated as Relevant Intelligence':
            if item.jurisdiction_confirmed is not True: raise ValueError('JURISDICTION CONFIRMATION REQUIRED before final validation')
            if geography_mismatch(item).get('status')=='pending': raise ValueError('GEOGRAPHIC MISMATCH — REVIEW REQUIRED before final validation')
            triage=triage_review_status(item)
            if triage['generated'] and triage['state']!='REVIEW COMPLETE':
                raise ValueError(f"AI TRIAGE REVIEW INCOMPLETE — {triage['reviewed']} of {triage['total']} generated suggestions decided")
        item.review_status=decision; item.review_notes=notes; item.assigned_reviewer=p['name']; item.validated_at=now(); db.commit(); audit(db,p,'IntelligenceItem',item.id,'REVIEWED',{'review_status':{'new':decision},'review_notes':{'new':item.review_notes},'triage_review':{'new':triage_review_status(item)},'human_approved_triage':{'new':human_approved_triage(item)}}); return {'ok':True}
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
        if not (item.original_content or '').strip(): raise ValueError('Original source content is required before AI Triage can be generated')
        run_id=str(uuid.uuid4())
        attempt_started=now()
        source_view=triage_source_view(item)
        triage_source=source_view['text']
        language_resolution=source_view['language']
        source_fp=hashlib.sha256(((item.original_content or '')+'|'+(item.source_url or '')).encode()).hexdigest()
        provider_meta={}
        fallback_code=''
        if openai_triage_configured():
            try:
                proposal,provider_meta=generate_openai_triage(item,run_id,source_text=triage_source,language_code=language_resolution.get('code'))
                if not _valid_v3_proposal(proposal): raise OpenAITriageError('provider_invalid_v3','OpenAI proposal did not satisfy the BAWASLU V3 contract')
                generator='openai-responses'
                generator_version=clean(provider_meta.get('model'),128) or 'configured-model'
                validation_outcome='VALID_V3_OPENAI'
            except OpenAITriageError as exc:
                fallback_code=exc.code
                proposal=_local_v3_triage(item,run_id,source_text=triage_source)
                generator='standalone-local-fallback'
                generator_version='v0.3'
                validation_outcome='FALLBACK_PROVIDER'
        else:
            proposal=_local_v3_triage(item,run_id,source_text=triage_source)
            generator='standalone-local-placeholder'
            generator_version='v0.3'
            validation_outcome='FALLBACK_NO_KEY'
            fallback_code='not_configured'
        if not _valid_v3_proposal(proposal): raise ValueError('AI Triage generator produced an invalid V3 proposal contract')
        prop_fp=hashlib.sha256(jdump(proposal).encode()).hexdigest()
        field_names=[k for k in proposal.keys() if not k.startswith('_')]
        generated_at=now()
        g=TriageGeneration(triage_run_id=run_id,intelligence_item_id=item.id,initiated_by_id=p['id'],source_fingerprint=source_fp,proposal_fingerprint=prop_fp,triage_schema_version=3,generator=generator,generator_version=generator_version,service_action='runTriage',attempt_started_at=attempt_started,attempt_ended_at=generated_at,generated_at=generated_at,validation_outcome=validation_outcome,proposal_field_names_json=jdump(field_names))
        db.add(g); item.ai_suggestions_json=jdump(proposal); item.updated_at=datetime.utcnow(); db.commit()
        review_state=triage_review_status(item)
        generation={'triage_run_id':run_id,'triage_schema_version':3,'generator':generator,'generator_version':generator_version,'service_action':'runTriage','generated_at':g.generated_at,'validation_outcome':validation_outcome,'proposal_field_names':field_names,'source_cleaning':source_view['cleaning'],'language_resolution':language_resolution}
        if provider_meta:
            generation['provider_response_id']=provider_meta.get('response_id') or ''
            generation['usage']=provider_meta.get('usage') or {}
        if fallback_code: generation['fallback_code']=fallback_code
        audit(db,p,'IntelligenceItem',item.id,'AI_TRIAGE_GENERATED',{'triage_run_id':{'new':run_id},'generator':{'new':generator},'generator_version':{'new':generator_version},'validation_outcome':{'new':validation_outcome},'fallback_code':{'new':fallback_code or None},'provider_usage':{'new':provider_meta.get('usage') if provider_meta else None},'provider_response_id':{'new':provider_meta.get('response_id') if provider_meta else None},'triage_review':{'new':review_state}})
        return {'suggestions':proposal,'generation':generation,'triage_review':review_state,'geography':loads(item.ai_geography_json,{}),'watchlist_match':None}
    if action=='triageDecision':
        if not has(p,'review_ai_suggestions'): raise PermissionError('Not permitted')
        key=clean(data.get('key'),100); status=clean(data.get('status'),64); reason=clean(data.get('reason'),500); value=data.get('value')
        if status not in TRIAGE_DECISION_STATUSES: raise ValueError('Invalid human decision')
        sug,reviewable=_triage_reviewable(item)
        if key not in reviewable: raise ValueError('This AI suggestion is not available for human review')
        if status=='Human Rejected' and len(reason)<5: raise ValueError('A short human rejection reason is required')
        if status=='Human Modified' and (value is None or not str(value).strip()): raise ValueError('A modified human value is required')
        stored=loads(item.ai_suggestions_json,{})
        decisions=stored.setdefault('_decisions',{})
        previous=decisions.get(key)
        decisions[key]={'status':status,'value':value,'reason':reason,'reviewer':p['name'],'reviewer_id':p['id'],'decided_at':now()}
        item.ai_suggestions_json=jdump(stored); item.updated_at=datetime.utcnow(); db.commit()
        current=triage_review_status(item)
        approved=human_approved_triage(item)
        audit(db,p,'IntelligenceItem',item.id,'AI_SUGGESTION_DECIDED',{key:{'previous':previous,'new':decisions[key]},'triage_review':{'new':current},'human_approved_triage':{'new':approved}})
        return {'ok':True,'triage_review':current,'human_approved_triage':approved}
    if action=='linkWatchlist':
        if not has(p,'review_ai_suggestions'): raise PermissionError('Not permitted')
        wid=str(data.get('watchlist_id','')); w=db.get(WatchlistItem,int(wid)) if wid.isdigit() else None
        if not w or not allowed(p,w): raise ValueError('Watchlist item unavailable')
        decision=data.get('decision')
        if decision=='Link': item.watchlist_id=wid; ents=loads(item.related_entities_json,[]); item.related_entities_json=jdump(list(dict.fromkeys(ents+[w.name]))[:20])
        elif decision!='Reject': raise ValueError('Invalid decision')
        db.commit(); audit(db,p,'IntelligenceItem',item.id,'WATCHLIST_MATCH_REVIEWED',{'watchlist_id':{'new':wid if decision=='Link' else None},'decision':{'new':decision}}); return {'ok':True}
    if action=='recoverSource':
        if not has(p,'edit_intelligence'): raise PermissionError('Not permitted')
        if item.source_type!='MANUAL_LINK' or not item.source_url: raise ValueError('Public URL source required')
        automatic=bool(data.get('automatic'))
        retrieved=fetch_public_source(item.source_url) if automatic else data
        changes,recovered=apply_source_recovery(item,retrieved)
        db.commit(); db.refresh(item)
        if changes:
            audit(db,p,'IntelligenceItem',item.id,'SOURCE_RECOVERED' if automatic else 'SOURCE_FIELDS_COMPLETED',changes)
        return {
          'ok':True,
          'item':intelligence(item),
          'recovered_fields':recovered,
          'retrieval_status':retrieved.get('retrieval_status','MANUAL_COMPLETION'),
          'message':'Recovered missing source fields.' if recovered else 'No missing source fields were changed.'
        }
    raise ValueError('Unknown action')
