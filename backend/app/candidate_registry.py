"""Officer-approved alias matching to already persisted Watchlist Candidate IDs.

No model requests; names alone are not identity verification.
"""
import json
import re
from .models import WatchlistItem
from .access import allowed

BLOCKED_ALIASES={'pemilu','pilkada','caleg','calon','presiden','bawaslu','kpu','warga'}
MAX_ALIASES=30

def normalized(value):
    return ' '.join(str(value or '').casefold().split())

def validate_aliases(value,canonical=''):
    if not isinstance(value,list) or len(value)>MAX_ALIASES:
        raise ValueError('Candidate aliases must be a list of at most 30 names')
    result=[]
    names=set()
    for item in value:
        if not isinstance(item,str):
            raise ValueError('Every candidate alias must be text')
        name=' '.join(item.split())
        key=normalized(name)
        if len(name)<3 or len(name)>120 or key in BLOCKED_ALIASES or not any(c.isalpha() for c in name):
            raise ValueError('A candidate alias is too short, generic or invalid')
        if key in names or key==normalized(canonical):continue
        names.add(key)
        result.append(name)
    return result

def aliases_for(row):
    try:
        parsed=json.loads(row.candidate_aliases_json or '[]')
    except (TypeError,ValueError):
        return []
    return parsed if isinstance(parsed,list) else []

def ensure_aliases_available(db, candidate_id, canonical_name, aliases):
    """Fail closed on collisions, including existing canonical registry names."""
    requested={normalized(n) for n in [canonical_name,*aliases]}
    for row in db.query(WatchlistItem).all():
        if row.id==candidate_id or row.type.casefold()!='candidate':
            continue
        existing={normalized(row.name),*(normalized(a) for a in aliases_for(row))}
        if requested & existing:
            raise ValueError('Candidate name or alias conflicts with another tracked candidate')

def candidate_index(db,p):
    """Index only authorized Watchlist candidate records, no leaked identities."""
    index={}
    for item in db.query(WatchlistItem).filter(WatchlistItem.type=='Candidate').all():
        if item.status=='Inactive' or not allowed(p,item):
            continue
        names=[item.name,*aliases_for(item)]
        for n in names:
            key=normalized(n)
            if key:
                index.setdefault(key,set()).add((item.id,item.name,item.status))
    return index

def resolve_signals(signals,index):
    from .processing_hints import normalize_candidate_signals
    resolved=[]
    seen=set()
    for raw in signals if isinstance(signals,list) else []:
        name=raw if isinstance(raw,str) else (
            raw.get('name') or raw.get('value') or '' if isinstance(raw,dict) else '')
        name=' '.join(str(name).split())
        key=normalized(name)
        if not key or key in seen:continue
        seen.add(key)
        found=index.get(key,set())
        # Known aliases are hints, not automatic identity confirmation.
        if not found:
            canonical=normalize_candidate_signals([name])
            if canonical:
                found=index.get(normalized(canonical[0]),set())
        if len(found)==1:
            record_id,canonical_name,status=next(iter(found))
            resolved.append({'source_name':name,'canonical_name':canonical_name,
                'canonical_candidate_id':'candidate:'+str(record_id),
                'identity_status':'TRACKED_CANDIDATE_MATCH_REQUIRES_VERIFICATION',
                'watchlist_status':status})
        elif len(found)>1:
            resolved.append({'source_name':name,'canonical_candidate_id':None,
                'identity_status':'AMBIGUOUS_CANDIDATE_ALIAS'})
        else:
            resolved.append({'source_name':name,'canonical_candidate_id':None,
                'identity_status':'UNMATCHED_CANDIDATE_NAME'})
    return resolved

def attach_candidate_ids(db,p,rows):
    idx=candidate_index(db,p)
    match_count=0
    unmatched_count=0
    ambiguous_count=0
    for row in rows:
        matches=resolve_signals(row.get('candidate_signals') or [],idx)
        row['candidate_identity_matches']=matches
        row['canonical_candidate_ids']=[m['canonical_candidate_id'] for m in matches
            if m.get('canonical_candidate_id')]
        # An absent, generic, unknown or ambiguous identity is a valid
        # no-candidate classification, not a processing failure.
        row['candidate_classification']='MATCHED' if row['canonical_candidate_ids'] else 'NO_CANDIDATE'
        row['candidate_classification_requires_manual_qa']=False
        match_count+=sum(bool(x.get('canonical_candidate_id')) for x in matches)
        unmatched_count+=sum(x['identity_status']=='UNMATCHED_CANDIDATE_NAME' for x in matches)
        ambiguous_count+=sum(x['identity_status']=='AMBIGUOUS_CANDIDATE_ALIAS' for x in matches)
    return {'no_candidate_posts':sum(
                row['candidate_classification']=='NO_CANDIDATE' for row in rows),
            'candidate_absence_is_valid':True,
            'requires_candidate_manual_qa':False,
            'matched_mentions':match_count,'unmatched_mentions':unmatched_count,
            'ambiguous_mentions':ambiguous_count,
            'registry_candidates_in_scope':len({t[0] for v in idx.values() for t in v}),
            'identity_is_legally_verified':False,
            'paid_provider_called':False}
