"""Live Smart Radar findings from the EXACT authorized Intelligence Inbox evidence.

This module does not query pilot source posts, run AI, invent event clusters, or
promote phrase-only leads to legal violations. A source is counted once even
when more than one permitted campaign links it. Findings carry stable IDs
for separate human triage (not a legal finding or an Inbox flag override).
"""
from collections import Counter
from hashlib import sha256
import re

RELEVANT={'RELEVANT','HIGHLY_RELEVANT'}

def _safe_strings(values):
    if not isinstance(values,list):
        return []
    out=[]
    for value in values:
        if isinstance(value,str) and value.strip():
            out.append(value.strip()[:120])
    return list(dict.fromkeys(out))

def _geo_mentions(row):
    """Geographic labels recorded in saved assessment; NOT incident verification."""
    found=set()
    for entry in row.get('location_signals') or []:
        if not isinstance(entry,dict):continue
        label=entry.get('province') or entry.get('name')
        if not isinstance(label,str):continue
        label=' '.join(label.split())[:128]
        if label and len(label)>1:
            found.add(label)
    return sorted(found)


def _verified_incident_province(row):
    """Only a current human-confirmed incident jurisdiction can count as verified."""
    review=row.get('incident_jurisdiction_review') or {}
    if not isinstance(review,dict):return ''
    if review.get('decision')!='CONFIRMED' or not review.get('incident_jurisdiction_verified'):
        return ''
    province=review.get('incident_province')
    return ' '.join(province.split())[:128] if isinstance(province,str) else ''


def _candidate_names(row):
    from .processing_hints import normalize_candidate_signals
    names=normalize_candidate_signals(_safe_strings(row.get('normalized_candidate_names')))
    if names:return names
    raw=row.get('candidate_signals') or []
    if not isinstance(raw,list):return []
    result=[]
    for item in raw:
        name=item if isinstance(item,str) else (item.get('name') or item.get('value') or '') if isinstance(item,dict) else ''
        if isinstance(name,str) and name.strip():result.append(name.strip()[:120])
    return normalize_candidate_signals(result)

def _category(row):
    for signal in row.get('potential_issues') or []:
        if isinstance(signal,dict) and isinstance(signal.get('category_name'),str):
            return signal['category_name'][:120]
    return ''

def _surface_issues(evidence):
    """Describe only phrases grounded in saved source evidence; no new legal verdict."""
    patterns=(
        (r'mencoblos lebih dari sekali|multiple ballots|multiple voting','possible repeat voting'),
        (r'demo|demonstrasi|people power|unjuk rasa','public demonstrations questioning election oversight'),
        (r'kecurangan|fraud|dicurangi','allegations of election irregularities'),
        (r'netralitas|tidak netral|keberpihakan','questions about officials\' impartiality'),
        (r'politik uang|serangan fajar|money politics','possible vote buying'),
        (r'daftar pemilih|voter registration','questions about voter-registration records'),
    )
    topics=[]
    for source in evidence:
        body=str(source.get('message_original') or '').casefold()
        for expression,description in patterns:
            if re.search(expression,body) and description not in topics:
                topics.append(description)
    return topics[:3]

def _saved_concern_summary(row):
    signal=next((x for x in row.get('public_concern_signals') or []
        if isinstance(x,dict) and (x.get('concern') or x.get('evidence_quote'))),None)
    if not signal:
        return 'A public concern was recorded and remains subject to further review.'
    description=str(signal.get('concern') or '').strip()
    if description:
        description=re.sub(r'\s+',' ',description)[:220].rstrip(' .')
        return 'Citizens report concerns: '+description+'. The claims and their wider impact require checking.'
    quote=str(signal.get('evidence_quote') or '')
    if quote:
        return 'A public concern refers to: “'+re.sub(r'\s+',' ',quote)[:140].strip()+'”. The report requires checking.'
    return 'A public concern was recorded and remains subject to further review.'

def _source(row):
    rid=str(row.get('id') or '')
    cid=str(row.get('campaign_id') or '')
    return {
        'canonical_source_id':'social:'+rid,
        'result_id':rid,'campaign_id':cid,
        'account_raw':str(row.get('author_name') or 'Unknown account')[:255],
        'published_at_raw':str(row.get('published_at') or '')[:64],
        'message_original':str(row.get('text_content') or '')[:5000],
        'source_url':str(row.get('canonical_url') or ''),
        'platform':str(row.get('platform') or 'Unknown'),
        'assessment_version':row.get('assessment_version'),
        'sentiment':str(row.get('sentiment') or 'UNCLASSIFIED').upper(),
        'geographic_mentions_unverified':_geo_mentions(row),
        'verified_incident_province':_verified_incident_province(row),
        'review_status':row.get('flag_review_status'),
        'source_verification_status':'SAVED_INBOX_ASSESSMENT_UNVERIFIED',
    }

NARRATIVE_DESCRIPTION={
    'Voter register accuracy':('questions about voter-register accuracy and whether registration information is up to date','These posts do not establish that voter records are incorrect.'),
    'Election money politics':('reports and discussion about possible vote buying','The allegations require checking; they are not proof of wrongdoing.'),
    'BAWASLU institutional trust':('public confidence in BAWASLU and questions about institutional impartiality','Opinions and accusations about impartiality should not be treated as established facts.'),
    'Election dispute proceedings':('election-related disputes and official proceedings','References to a dispute do not establish that any party acted improperly.'),
    'Candidate nomination process':('questions about candidate nomination and verification procedures','A procedural discussion is not itself a violation allegation.'),
    'Participatory election oversight':('citizen participation in monitoring elections','The discussion does not by itself indicate a breach of election rules.'),
}

def narrative_summary(subject,count,candidate_mentions):
    """Two-sentence, plain-language, strictly evidence-limited thematic overview.

    Only anchored patterns from source text are summarized here. A candidate
    may be named as contextual mention, never as an alleged wrongdoer.
    """
    description,caveat=NARRATIVE_DESCRIPTION.get(subject,(
        'a recurring election-related topic','The underlying claims need independent checking.'))
    mentions=sorted((candidate_mentions or {}).items(),key=lambda pair:(-pair[1],pair[0]))
    candidate_note=(' The posts also mention '+', '.join(name for name,_ in mentions[:2])+'.'
                    if mentions and count>=2 else '')
    return ('Discussion trends: '+str(count)+' posts from different sources refer to '+
            description+'. '+caveat+candidate_note)

def compile_inbox_findings(rows,states=None):
    """Pure, deterministic grouping of saved, relevant Inbox records.

    Explicit saved violations remain one finding per source, so distinct
    allegations never merge into an invented incident. Public concerns and
    topics may group as *discussion*, never as verified incidents.
    """
    states=states or {}
    selected={}
    # The Inbox has already applied campaign and jurisdiction permissions.
    # One original social source must not inflate totals across campaigns.
    for row in rows or []:
        if not isinstance(row,dict):continue
        if str(row.get('relevance_label') or '').upper() not in RELEVANT:continue
        rid=str(row.get('id') or '')
        cid=str(row.get('campaign_id') or '')
        if not rid.isdigit() or not cid.isdigit():continue
        if rid not in selected:
            selected[rid]=row
    grouped={}
    for row in selected.values():
        rid=str(row['id'])
        cid=str(row['campaign_id'])
        flagged=row.get('is_flagged') is True and row.get('flag_review_status')!='FLAG_DISMISSED'
        concerns=row.get('public_concern_signals')
        has_concern=isinstance(concerns,list) and bool(concerns)
        topics=_safe_strings(row.get('topic_labels'))
        topic=topics[0] if topics else ''
        if flagged:
            key='INBOX-V-'+cid+'-'+rid
            title='Potential violation review · '+(_category(row) or 'Officer-reviewed signal')
            players=['violations']
            if has_concern:players.append('concerns')
            kind='source_review'
        elif has_concern:
            key=('INBOX-C-'+sha256(topic.casefold().encode()).hexdigest()[:16]) if topic else 'INBOX-C-'+cid+'-'+rid
            title='Public concern discussion'+(' · '+topic if topic else '')
            players=['concerns']
            kind='discussion'
        elif topic:
            from .processing_hints import narrative_anchors
            anchors=narrative_anchors(row.get('text_content'))
            if anchors:
                anchor=anchors[0]
                key='INBOX-N-'+sha256(anchor.casefold().encode()).hexdigest()[:16]
                title='Discussion · '+anchor
                players=['narratives']
                kind='narrative_candidate'
            else:
                key='INBOX-S-'+cid+'-'+rid
                title='Relevant source for officer review'
                players=[]
                kind='source_awareness'
        else:
            key='INBOX-S-'+cid+'-'+rid
            title='Relevant source for officer review'
            players=[]
            kind='source_awareness'
        if key not in grouped:
            grouped[key]={
                'id':key,'title':title[:200],'kind':kind,
                'players':players,'perspectives':set(),'topics':set(),
                'posts':[],'platform_counts':Counter(),'day_counts':Counter(),
                'sentiment_counts':Counter(),'actor_mentions':Counter(),
                'geo_signal_counts':Counter(),'verified_incident_counts':Counter(),
                'published_at':'','source_ids':[],
                'attention':bool(flagged or has_concern),
                'concern_descriptions':[],
                'source_assessment_versions':[],
                'priority_score':None,'priority_label':'Not AI-scored',
            }
        g=grouped[key]
        source=_source(row)
        g['posts'].append(source)
        g['source_ids'].append(source['canonical_source_id'])
        g['source_assessment_versions'].append({'source_id':source['canonical_source_id'],
            'campaign_id':cid,'assessment_version':row.get('assessment_version')})
        g['platform_counts'][source['platform']]+=1
        day=source['published_at_raw'][:10]
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):g['day_counts'][day]+=1
        sentiment=source['sentiment']
        g['sentiment_counts'][sentiment if sentiment in ('POSITIVE','NEGATIVE','NEUTRAL') else 'UNCLASSIFIED']+=1
        g['actor_mentions'].update(_candidate_names(row))
        g['geo_signal_counts'].update(source['geographic_mentions_unverified'])
        if source['verified_incident_province']:
            g['verified_incident_counts'][source['verified_incident_province']]+=1
        g['topics'].update(topics)
        if flagged:g['topics'].add('Potential Violations')
        if has_concern:
            g['topics'].add('Public Concerns')
            g['concern_descriptions'].append(_saved_concern_summary(row))
        if 'BAWASLU Reputation' in topics:g['perspectives'].add('reputation')
        # Operational alerts and complaints must remain available in the
        # primary Command Centre view even when they concern BAWASLU itself.
        if flagged or has_concern or 'Electoral Operations' in topics or 'BAWASLU Reputation' not in topics:
            g['perspectives'].add('operations')
        g['published_at']=max(g['published_at'],source['published_at_raw'])
    findings=[]
    for key,g in grouped.items():
        evidence=g['posts']
        unique_urls={p['source_url'] for p in evidence if p['source_url']}
        unique_authors={p['account_raw'].casefold() for p in evidence if p['account_raw']!='Unknown account'}
        recurring=len(unique_urls)>=2 and len(unique_authors)>=2
        if g['kind']=='narrative_candidate' and not recurring:
            g['players']=[]
            g['kind']='source_awareness'
        if g['kind']=='discussion' and recurring:
            g['title']=g['title'].replace('Monitored discussion','Recurring discussion')
        if g['kind']=='source_review':
            subjects=_surface_issues(evidence)
            g['summary']=('Reports raise '+(', '.join(subjects))+'. These allegations require verification.'
                          if subjects else
                          'An original post contains a saved potential election-rule concern. Its allegations still require verification.')
        elif g['kind']=='narrative_candidate':
            subject=g['title'].split(' · ',1)[-1]
            g['summary']=narrative_summary(subject,len(evidence),g['actor_mentions'])
        elif g['kind']=='discussion':
            g['summary']=g['concern_descriptions'][0] if g['concern_descriptions'] else (
                'Several source posts discuss '+(g['title'].split(' · ',1)[-1] if ' · ' in g['title'] else 'a public issue')+
                '. Any reported problems require independent checking.')
        else:
            g['summary']='This election-related post is being monitored. Its topic has not yet been identified.'
        state=states.get(key) or {}
        g['status']=state.get('status') or ('pending' if g['attention'] else 'awareness')
        g['human_reviewed']=bool(state.get('first_reviewed_at'))
        g['next_followup']=str(state.get('next_followup') or '')
        g['updated_at']=str(state.get('updated_at') or '')
        g['review_suggested']=g['attention']
        g['review_basis']='Saved Inbox assessment, officer triage required'
        g['priority_label']='Review suggested · Unscored' if g['attention'] else 'Awareness · Unscored'
        g['topics']=sorted(g['topics'])
        g['perspectives']=sorted(g['perspectives']) or ['operations']
        g['supporting_posts']=len(evidence)
        g['insights']={side:g['summary'] for side in ('operations','reputation')}
        g['ai_summary']=False
        g['ai_model']=''
        g['summary_evidence_sample']=None
        g['source_signature']=sha256(('|'.join(sorted(g['source_ids']))).encode()).hexdigest()
        g['platform_counts']=dict(g['platform_counts'])
        g['day_counts']=dict(g['day_counts'])
        g['sentiment_counts']=dict(g['sentiment_counts'])
        g['actor_mentions']=dict(g['actor_mentions'])
        g['geo_signal_counts']=dict(g['geo_signal_counts'])
        g['verified_incident_counts']=dict(g['verified_incident_counts'])
        g['recurring_discussion']=recurring
        g['source_evidence_verified']=False
        g['paid_provider_called']=False
        g['geography']='Incident geography not inferred'
        g.pop('attention')
        g.pop('concern_descriptions',None)
        findings.append(g)
    return sorted(findings,key=lambda x:(x['status']!='pending',-x['supporting_posts'],x['title'],x['id']))

def live_inbox_findings(db,principal,states=None):
    from .campaigns import campaign_action
    from .inbox_read_cache import read as cached_inbox
    inbox=cached_inbox(principal,{'campaign_id':None,'result_id':None,'id':None},
        lambda:campaign_action(db,principal,'campaignIntelligenceInbox',{}))
    rows=inbox.get('findings') or []
    return compile_inbox_findings(rows,states),inbox
