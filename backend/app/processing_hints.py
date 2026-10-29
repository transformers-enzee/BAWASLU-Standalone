"""No-cost, conservative source-text processing hints for human review.

These are descriptive candidates, not legal conclusions or jurisdiction grants.
"""
import hashlib
import re

PROVINCE_ALIASES={
    'riau':'Riau', 'jawa timur':'Jawa Timur','jatim':'Jawa Timur',
    'jawa barat':'Jawa Barat','jabar':'Jawa Barat',
    'jawa tengah':'Jawa Tengah','jateng':'Jawa Tengah',
    'sumatera barat':'Sumatera Barat','sumbar':'Sumatera Barat',
    'sumatera utara':'Sumatera Utara','sumut':'Sumatera Utara',
    'bali':'Bali','dki jakarta':'DKI Jakarta','jakarta':'DKI Jakarta',
}
TOPIC_TERMS={
    'Electoral Operations':('kpu','pemilu','pemilihan','pengawasan','dkpp','pencalonan','pelanggaran pemilu'),
    'BAWASLU Reputation':('reputasi bawaslu','kepercayaan publik terhadap bawaslu','kritik terhadap bawaslu','citra bawaslu'),
}
ROUTINE_MARKERS=('selamat hari','sumpah pemuda','dirgahayu','selamat ulang tahun','ucapan selamat','memperingati hari')
SUBSTANTIVE_MARKERS=('pelanggaran','dugaan','laporan','investigasi','pengawasan pemilu','pemungutan suara','sengketa','kecurangan','putusan dkpp','temuan')
def communication_context(text):
    """Conservative triage hint; never silently overrides an AI or human label."""
    body=str(text or '').casefold()
    greeting=any(term in body for term in ROUTINE_MARKERS)
    substantive=any(term in body for term in SUBSTANTIVE_MARKERS)
    if greeting and not substantive:
        return {'category':'ROUTINE_COMMUNICATION','actionability':'NOT_ESTABLISHED','requires_human_review':True}
    return {'category':'UNRESOLVED','actionability':'NOT_ESTABLISHED','requires_human_review':True}

def triage_disposition(text, relevance_label):
    """Advisory only. Never modifies saved assessment or bypasses review."""
    context=communication_context(text)
    label=str(relevance_label or '').upper()
    if context['category']=='ROUTINE_COMMUNICATION' and label in ('RELEVANT','HIGHLY_RELEVANT'):
        return 'REVIEW_RELEVANCE'
    if label in ('RELEVANT','HIGHLY_RELEVANT'):
        return 'RELEVANT_REVIEWED_BY_AI'
    return 'NOT_AI_RELEVANT'

CANDIDATE_ALIASES={
    'Prabowo Subianto':('prabowo subianto',),
    'Gibran Rakabuming Raka':('gibran rakabuming raka','gibran rakabuming'),
}
def normalize_candidate_signals(signals):
    """Resolve only an explicitly known full-name alias; retain unknowns unaltered."""
    resolved=[]
    for signal in signals or []:
        if isinstance(signal,str):
            name=signal
        elif isinstance(signal,dict):
            name=signal.get('name') or signal.get('value') or ''
        else:
            continue
        clean=re.sub(r'\\s+',' ',str(name)).strip()
        if not clean:continue
        canonical=next((person for person,aliases in CANDIDATE_ALIASES.items()
            if clean.casefold() in aliases),clean)
        if canonical not in resolved:resolved.append(canonical)
    return resolved

def classification_evidence(text):
    """Issue terminology is a review cue, never a finding or legal verdict."""
    value=str(text or '')
    terms=('dugaan pelanggaran','laporan pelanggaran','sengketa pemilu','politik uang','kecurangan pemilu')
    matches=[term for term in terms if re.search(r'(?<!\\w)'+re.escape(term)+r'(?!\\w)',value.casefold())]
    return {'potential_issue_phrase_matches':matches,
            'potential_violation_confirmed':False,
            'needs_human_validation':bool(matches),
            'sentiment':'UNCLASSIFIED',
            'sentiment_basis':'NOT_AI_ASSESSED'}

def source_hints(text):
    body=str(text or '')
    folded=body.casefold()
    topics=[name for name,terms in TOPIC_TERMS.items() if any(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',folded) for t in terms)]
    provinces=sorted({standard for alias,standard in PROVINCE_ALIASES.items()
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',folded)})
    normalized=re.sub(r'\s+',' ',folded).strip()
    return {
        'topic_suggestions':topics,
        'issue_screening':classification_evidence(body),
        'communication_context':communication_context(body),
        'province_mentions':provinces,
        'incident_jurisdiction_status':'UNVERIFIED',
        'province_mentions_are_incident_location':False,
        'exact_text_fingerprint':hashlib.sha256(normalized.encode('utf-8')).hexdigest() if normalized else None,
        'classification_method':'RULE_HINTS_V1',
    }

def summarize_scoped_findings(records):
    """Deterministic, read-only aggregation of ALREADY authorized relevant findings.

    Grouping is preliminary: exact duplicate fingerprints and source URLs are
    not incident identity. Topic grouping is not emerging-narrative detection.
    """
    from collections import defaultdict
    buckets=defaultdict(list)
    topic_groups=defaultdict(list)
    attention=[]
    players={'Potential Violations':[],'Public Concerns':[],
        'Emerging Narratives':[],'Needs Attention':[],'Reviewed History':[]}
    for row in records:
        rid=str(row.get('id') or '')
        campaign=str(row.get('campaign_id') or '')
        metadata=row.get('processing_hints') or source_hints(row.get('text_content'))
        fingerprint=metadata.get('exact_text_fingerprint')
        url=str(row.get('canonical_url') or '').strip().casefold()
        # Campaign-specific grouping never crosses visibility boundaries.
        if url:
            buckets[(campaign,'url',url)].append(rid)
        elif fingerprint:
            buckets[(campaign,'text',fingerprint)].append(rid)
        for topic in metadata.get('topic_suggestions') or []:
            topic_groups[topic].append(rid)
        key={'result_id':rid,'campaign_id':campaign}
        issue=bool(row.get('potential_issues'))
        flag=bool(row.get('is_flagged'))
        reviewed=bool(row.get('flag_review_status'))
        if issue:
            players['Potential Violations'].append({**key,'status':'PRELIMINARY_SIGNAL'})
        if reviewed:
            players['Reviewed History'].append({**key,'review_status':row.get('flag_review_status')})
        if issue or flag:
            attention.append({**key,'reason':'EXISTING_ISSUE_OR_HUMAN_FLAG','status':'PRELIMINARY_REVIEW'})
            players['Needs Attention'].append({**key,'status':'PENDING_HUMAN_TRIAGE'})
        # Text alone cannot prove a public concern or an emerging narrative.
        # Those players intentionally remain empty until supporting assessments exist.
    duplicates=[{'campaign_id':key[0],'source_ids':ids,'basis':'EXACT_URL_OR_TEXT'}
        for key,ids in buckets.items() if len(ids)>1]
    return {'visible_relevant_count':len(records),
        'exact_duplicate_groups':duplicates,
        'topic_groups':[{'topic':name,'source_ids':ids,'count':len(ids),'status':'KEYWORD_GROUP_ONLY'}
            for name,ids in sorted(topic_groups.items())],
        'needs_attention_candidates':attention,
        'intelligence_players':{name:{'entries':items,'count':len(items)} for name,items in players.items()},
        'player_classification_scope':'EXISTING_SIGNALS_AND_REVIEWS_ONLY',
        'incident_clusters_verified':0,
        'narratives_verified':0,
        'status':'DERIVED_FROM_AUTHORIZED_SAVED_ASSESSMENTS',
        'paid_provider_called':False}
