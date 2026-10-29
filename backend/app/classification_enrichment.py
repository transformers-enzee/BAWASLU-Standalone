"""Conservative one-call player/topic annotations with source-grounded QA.

No inferred guilt, no inferred geography, no automated enforcement. All output
is a provisional AI suggestion until a separate officer review is recorded.
"""
import hashlib
import json
import re
from .processing_hints import communication_context, public_concern_cues

TOPICS={'Public Information','Voter Registration','Electoral Operations','Campaign Rules','Public Concern','BAWASLU Reputation'}
PLAYERS={'Potential Violations','Public Concerns','Emerging Narratives',
         'Needs Attention'}
SCALES={'LOW','MEDIUM','HIGH','NOT_ASSESSED'}

def json_list(text):
    if isinstance(text,list):return text
    try:value=json.loads(text or '[]')
    except (ValueError,TypeError):return []
    return value if isinstance(value,list) else []

def json_obj(text):
    if isinstance(text,dict):return text
    try:value=json.loads(text or '{}')
    except (ValueError,TypeError):return {}
    return value if isinstance(value,dict) else {}

def normalize_topics(value, source_text, relevance):
    if str(relevance or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
        return []
    if not isinstance(value,list):return []
    categories=[x for x in sorted(TOPICS) if x in value]
    if communication_context(source_text)['category']=='ROUTINE_COMMUNICATION':
        return ['Public Information'] if 'Public Information' in categories else []
    return categories

def _valid_quote(quote,source,min_chars=15):
    return (isinstance(quote,str) and min_chars<=len(quote.strip())<=500 and
            quote.strip().casefold() in str(source or '').casefold())

def normalize_concerns(value,source_text,relevance):
    if str(relevance or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
        return []
    if not isinstance(value,list):return []
    # Explicit complaint cues avoid treating generic political discussion as
    # a public concern. This is intentionally conservative for false positives.
    if not public_concern_cues(source_text):return []
    result=[]
    for item in value[:5]:
        if not isinstance(item,dict):continue
        quote=item.get('evidence_quote')
        if not _valid_quote(quote,source_text):continue
        detail=str(item.get('concern') or '').strip()[:240]
        if not detail:continue
        result.append({'evidence_quote':quote.strip(),
            'concern':detail,'status':'AI_CONCERN_SIGNAL_UNVERIFIED',
            'legal_violation_confirmed':False})
    return result

def normalize_attention(value,source_text,eligible_signals,eligible_concerns):
    """No seriousness or urgency without quoted evidence to inspect."""
    if not isinstance(value,dict):return {}
    quote=value.get('evidence_quote')
    if not _valid_quote(quote,source_text,20):return {}
    if not (eligible_signals or eligible_concerns):return {}
    serious=str(value.get('seriousness') or '').upper()
    urgency=str(value.get('urgency') or '').upper()
    if serious not in SCALES:serious='NOT_ASSESSED'
    if urgency not in SCALES:urgency='NOT_ASSESSED'
    return {'seriousness':serious,'urgency':urgency,
            'evidence_quote':quote.strip(),
            'evidence_quality':'SOURCE_QUOTED_UNCORROBORATED',
            'actionability':'HUMAN_TRIAGE_ONLY',
            'status':'AI_ASSESSMENT_UNVERIFIED',
            'legal_violation_confirmed':False}

def normalize_summaries(value,source_text,relevance):
    if str(relevance or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
        return []
    if not isinstance(value,list):return []
    result=[]
    for row in value[:8]:
        if not isinstance(row,dict):continue
        player=row.get('player')
        summary=row.get('summary')
        quote=row.get('source_quote')
        if player not in PLAYERS or not isinstance(summary,str):
            continue
        text=summary.strip()
        if not (10<=len(text)<=500 and _valid_quote(quote,source_text,15)):
            continue
        # A draft with categorical guilt claims is not a defensible finding.
        if re.search(r'\b(terbukti bersalah|sudah pasti melanggar|confirmed guilty|proven guilty)\b',
                     text.casefold()):
            continue
        result.append({'player':player,'summary':text,
            'source_quote':quote.strip(),
            'provenance':'PRODUCTION_AI_PIPELINE',
            'source_text_sha256':hashlib.sha256(str(source_text or '').strip().encode('utf-8')).hexdigest(),
            'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW',
            'legal_violation_confirmed':False})
    return result

def token_usage(raw):
    """Works with Chat Completions and Responses API usage formats."""
    if not isinstance(raw,dict):raw={}
    found=any(k in raw for k in
              ('prompt_tokens','completion_tokens','input_tokens','output_tokens'))
    def number(*keys):
        for key in keys:
            x=raw.get(key)
            if isinstance(x,int) and not isinstance(x,bool) and x>=0:
                return min(x,100000000)
        return 0
    return {'input_tokens':number('input_tokens','prompt_tokens'),
        'output_tokens':number('output_tokens','completion_tokens'),
        'usage_reported':found,
        'cost_usd':'','cost_status':'NOT_REPORTED_BY_PROVIDER'}
