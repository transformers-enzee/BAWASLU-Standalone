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

NARRATIVE_ANCHORS={
    'Voter register accuracy':('daftar pemilih','pdpb','daftar pemilih tetap'),
    'Election money politics':('politik uang','serangan fajar'),
    'BAWASLU institutional trust':('reputasi bawaslu','kepercayaan publik terhadap bawaslu',
        'kritik terhadap bawaslu','citra bawaslu','bawaslu tidak netral','bawaslu berpihak'),
    'Election dispute proceedings':('sengketa pemilu','sengketa pilkada','putusan dkpp'),
    'Candidate nomination process':('proses pencalonan','pendaftaran calon','verifikasi calon'),
}
def _term_present(body,term):
    return bool(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',body))

def narrative_anchors(text):
    """Specific recurring-discussion cues, never proof of a shared incident."""
    body=str(text or '').casefold()
    if not body or communication_context(body)['category']=='ROUTINE_COMMUNICATION':
        return []
    return [name for name,terms in NARRATIVE_ANCHORS.items()
            if any(_term_present(body,term) for term in terms)]

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
    seen=set()
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
        if canonical.casefold() not in seen:
            resolved.append(canonical)
            seen.add(canonical.casefold())
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
    topics=[] if communication_context(body)['category']=='ROUTINE_COMMUNICATION' else [name for name,terms in TOPIC_TERMS.items() if any(_term_present(folded,t) for t in terms)]
    provinces=sorted({standard for alias,standard in PROVINCE_ALIASES.items()
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',folded)})
    normalized=re.sub(r'\s+',' ',folded).strip()
    return {
        'topic_suggestions':topics,
        'narrative_anchors':narrative_anchors(body),
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
            'narrative_anchors':hints.get('narrative_anchors') or [],
            'location_mentions_unverified':hints.get('province_mentions') or [],
            'potential_issues':row.get('potential_issues') or [],
            'review_status':row.get('flag_review_status'),
            'assessment_version':row.get('assessment_version')}


def exact_source_groups(records):
    """Exact normalized-text duplicates, isolated per campaign.

    A URL may host distinct comments or modified content; URL-only matches
    must not merge incident evidence. Shared text does not verify an incident.
    """
    from collections import defaultdict
    groups=defaultdict(set)
    for row in records:
        campaign=str(row.get('campaign_id') or '')
        rid=str(row.get('id') or '')
        fingerprint=source_hints(row.get('text_content'))['exact_text_fingerprint']
        if rid and fingerprint:
            groups[(campaign,fingerprint)].add(rid)
    return [{'campaign_id':campaign,'post_ids':sorted(ids),
             'incident_verified':False}
            for (campaign,_),ids in sorted(groups.items()) if len(ids)>1]


def emerging_narrative_candidates(records):
    """Unverified recurring discussions, never confirmed incident clusters.

    Require three distinct relevant posts, URLs and posting accounts.
    Reposted identical text contributes only one post to a candidate.
    """
    from collections import defaultdict
    grouped=defaultdict(list)
    for row in records:
        if str(row.get('relevance_label') or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
            continue
        campaign=str(row.get('campaign_id') or '')
        rid=str(row.get('id') or '')
        author=str(row.get('author_name') or '').strip().casefold()
        url=str(row.get('canonical_url') or '').strip().casefold()
        body=row.get('text_content')
        fingerprint=source_hints(body)['exact_text_fingerprint']
        if not (campaign and rid and author and url and fingerprint):
            continue
        for anchor in narrative_anchors(body):
            grouped[(campaign,anchor)].append((rid,author,url,fingerprint))
    candidates=[]
    for (campaign,anchor),items in sorted(grouped.items()):
        by_fingerprint={}
        for item in items:
            by_fingerprint.setdefault(item[3],item)
        evidence=list(by_fingerprint.values())
        if len(evidence)<3 or len({x[1] for x in evidence})<3 or len({x[2] for x in evidence})<3:
            continue
        candidates.append({'campaign_id':campaign,'anchor':anchor,
            'source_ids':sorted(x[0] for x in evidence),'distinct_posts':len(evidence),
            'distinct_authors':len({x[1] for x in evidence}),
            'distinct_urls':len({x[2] for x in evidence}),
            'status':'RECURRING_DISCUSSION_CANDIDATE',
            'evidence_independence':'UNVERIFIED','incident_verified':False})
    return candidates


def summarize_scoped_findings(records):
    """Read-only, authorized saved-assessment aggregation; no model requests."""
    from collections import defaultdict
    topic_groups=defaultdict(list)
    attention=[]
    players={'Potential Violations':[],'Public Concerns':[],
        'Emerging Narratives':[],'Needs Attention':[],'Reviewed History':[]}
    for row in records:
        rid=str(row.get('id') or '')
        campaign=str(row.get('campaign_id') or '')
        metadata=row.get('processing_hints') or source_hints(row.get('text_content'))
        for topic in metadata.get('topic_suggestions') or []:
            topic_groups[topic].append(rid)
        key={'result_id':rid,'campaign_id':campaign}
        issue=bool(row.get('potential_issues'))
        flag=bool(row.get('is_flagged'))
        status=str(row.get('flag_review_status') or '').upper()
        dismissed=status=='FLAG_DISMISSED'
        if issue and not dismissed:
            players['Potential Violations'].append({**key,'status':'PRELIMINARY_SIGNAL'})
        if status:
            players['Reviewed History'].append({**key,'review_status':status})
        if (issue or flag) and not dismissed:
            attention.append({**key,'reason':'SAVED_ISSUE_OR_HUMAN_FLAG',
                'status':'FURTHER_INVESTIGATION' if status=='FURTHER_INVESTIGATION' else 'PRELIMINARY_REVIEW',
                'seriousness':'NOT_ASSESSED','urgency':'NOT_ASSESSED',
                'evidence_quality':'UNVERIFIED','actionability':'HUMAN_TRIAGE_ONLY'})
            players['Needs Attention'].append({**key,'status':'PENDING_HUMAN_TRIAGE'})
    duplicates=[{'campaign_id':group['campaign_id'],'source_ids':group['post_ids'],
                 'basis':'EXACT_NORMALIZED_TEXT'} for group in exact_source_groups(records)]
    narratives=emerging_narrative_candidates(records)
    for narrative in narratives:
        players['Emerging Narratives'].append({
            'campaign_id':narrative['campaign_id'],
            'source_ids':narrative['source_ids'],
            'anchor':narrative['anchor'],
            'status':'REQUIRES_HUMAN_REVIEW'})
    missing_fields={'text_content':0,'canonical_url':0,'campaign_id':0,
                    'sentiment':0,'assessment_version':0}
    for row in records:
        for field in missing_fields:
            value=row.get(field)
            if value is None or value=='' or value=='UNKNOWN' or value=='UNCLASSIFIED':
                missing_fields[field]+=1
    return {'visible_relevant_count':len(records),
        'classification_contracts':[classification_contract(row) for row in records],
        'exact_source_groups':exact_source_groups(records),
        'exact_duplicate_groups':duplicates,
        'emerging_narrative_candidates':narratives,
        'topic_groups':[{'topic':name,'source_ids':ids,'count':len(ids),
                         'status':'KEYWORD_GROUP_ONLY'}
                        for name,ids in sorted(topic_groups.items())],
        'needs_attention_candidates':attention,
        'intelligence_players':{name:{'entries':items,'count':len(items)}
                                for name,items in players.items()},
        'player_classification_scope':'SAVED_SIGNALS_AND_UNVERIFIED_RECURRING_DISCUSSION_CANDIDATES',
        'processing_diagnostics':{'missing_field_counts':missing_fields,
            'failed_classifications_reported':False,
            'ai_usage_cost_reported':False,'scope':'VISIBLE_ROWS_ONLY'},
        'incident_clusters_verified':0,'narratives_verified':0,
        'status':'DERIVED_FROM_AUTHORIZED_SAVED_ASSESSMENTS',
        'paid_provider_called':False}
