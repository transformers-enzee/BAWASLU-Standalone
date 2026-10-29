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
        clean=re.sub(r'\s+',' ',str(name)).strip()
        if not clean:continue
        canonical=next((person for person,aliases in CANDIDATE_ALIASES.items()
            if clean.casefold() in aliases),clean)
        if canonical not in resolved:resolved.append(canonical)
    return resolved

def classification_evidence(text):
    """Issue terminology is a review cue, never a finding or legal verdict."""
    value=str(text or '')
    terms=('dugaan pelanggaran','laporan pelanggaran','sengketa pemilu','politik uang','kecurangan pemilu')
    matches=[term for term in terms if re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',value.casefold())]
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

def assessment_quality_snapshot(records):
    """Read-only classification coverage on authorized current assessment findings."""
    sentiments={'POSITIVE':0,'NEUTRAL':0,'NEGATIVE':0,'UNCLASSIFIED':0}
    issue_posts=0
    candidate_posts=0
    verified_locations=0
    for row in records:
        sentiment=str(row.get('sentiment') or 'UNCLASSIFIED').upper()
        sentiments[sentiment if sentiment in sentiments else 'UNCLASSIFIED']+=1
        issue_posts+=bool(row.get('potential_issues'))
        candidate_posts+=bool(row.get('normalized_candidate_names') or row.get('candidate_signals'))
        verified_locations+=bool(row.get('incident_jurisdiction_verified') is True)
    return {'visible_relevant_posts':len(records),'sentiment_counts':sentiments,
            'posts_with_existing_issue_signals':issue_posts,
            'posts_with_candidate_signals':candidate_posts,
            'verified_incident_jurisdiction_posts':verified_locations,
            'source':'AUTHORIZED_SAVED_FINDINGS_ONLY','paid_provider_called':False}

def classification_contract(row):
    """Reuse saved annotations; unverified mentions cannot grant regional access."""
    hints=row.get('processing_hints') or source_hints(row.get('text_content'))
    return {'result_id':str(row.get('id') or ''),
            'campaign_id':str(row.get('campaign_id') or ''),
            'relevance':str(row.get('relevance_label') or 'UNASSESSED').upper(),
            'sentiment':str(row.get('sentiment') or 'UNCLASSIFIED').upper(),
            'candidate_names':normalize_candidate_signals(row.get('candidate_signals') or []),
            'topics':hints.get('topic_suggestions') or [],
            'location_mentions_unverified':hints.get('province_mentions') or [],
            'potential_issues':row.get('potential_issues') or [],
            'review_status':row.get('flag_review_status'),
            'assessment_version':row.get('assessment_version')}


def exact_source_groups(records):
    """Exact-source duplicate grouping only; never assert same incident."""
    from collections import defaultdict
    grouped=defaultdict(list)
    for row in records:
        source=str(row.get('canonical_url') or '').strip().lower()
        fingerprint=source_hints(row.get('text_content'))['exact_text_fingerprint']
        campaign=str(row.get('campaign_id') or '')
        # Index both canonical URL and normalized content to catch cross-post
        # duplicate text. Use connected components to avoid double counting.
        rid=str(row.get('id') or '')
        if source:
            grouped[(campaign,'url',source)].append(rid)
        if fingerprint:
            grouped[(campaign,'text',fingerprint)].append(rid)
    parents={}
    def root(x):
        parents.setdefault(x,x)
        if parents[x]!=x:parents[x]=root(parents[x])
        return parents[x]
    for ids in grouped.values():
        if len(ids)<2:continue
        first=ids[0]
        for other in ids[1:]:
            a,b=root(first),root(other)
            if a!=b:parents[b]=a
    components=defaultdict(set)
    for (campaign,_,_),ids in grouped.items():
        for rid in ids:
            if rid in parents:components[(campaign,root(rid))].add(rid)
    return [{'campaign_id':key[0],'post_ids':sorted(ids,key=str),
             'incident_verified':False}
            for key,ids in sorted(components.items())
            if len(ids)>1]


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
    duplicates=[{'campaign_id':group['campaign_id'],'source_ids':group['post_ids'],
                 'basis':'EXACT_URL_OR_TEXT'} for group in exact_source_groups(records)]
    return {'visible_relevant_count':len(records),
        'classification_contracts':[classification_contract(x) for x in records],
        'exact_source_groups':exact_source_groups(records),
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
