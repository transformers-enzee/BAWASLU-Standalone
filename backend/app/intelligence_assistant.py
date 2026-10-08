import json, os, re
from datetime import datetime, timezone, timedelta
import httpx
from .openai_triage import openai_triage_configured, openai_triage_model, OPENAI_DEFAULT_BASE_URL
from .domain import human_approved_triage
from .source_retrieval import clean_article_text

class AssistantProviderError(RuntimeError):
    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code=code

STOPWORDS={
 'what','when','where','which','with','from','that','this','show','tell','about','are','the','and','for','into',
 'latest','summarise','summarize','intelligence','records','record','main','issues','highest','priority','today',
 'yang','dan','untuk','dari','dalam','apa','mana','terkini','ringkaskan','intelijen'
}

ANSWER_SCHEMA={
  'type':'object',
  'properties':{
    'answer_summary':{'type':'string'},
    'key_observations':{'type':'array','items':{'type':'string'},'maxItems':8},
    'evidence_status':{'type':'array','items':{'type':'string'},'maxItems':6},
    'limitations':{'type':'array','items':{'type':'string'},'maxItems':5},
    'cited_record_ids':{'type':'array','items':{'type':'string'},'maxItems':12}
  },
  'required':['answer_summary','key_observations','evidence_status','limitations','cited_record_ids'],
  'additionalProperties':False
}

SYSTEM_PROMPT="""You are the BAWASLU Intelligence Assistant. You answer questions only from the BAWASLU intelligence records supplied in the request.

Mandatory rules:
1. The supplied records have already been restricted to the current user's authorized geographic/access scope. Never imply access to any other records.
2. Use recorded source evidence and HUMAN-APPROVED triage values only. Never treat pending, rejected, or raw AI triage suggestions as approved intelligence.
3. Clearly distinguish source reporting, human-approved analytical fields, verification status, and uncertainty.
4. UNVERIFIED evidence must remain explicitly unverified. Human relevance validation is not the same as source verification.
5. Do not invent facts, actors, relationships, violations, legal conclusions, ownership, intent, or jurisdiction.
6. Cite the supporting intelligence IDs in observations using square brackets, for example [INT-2026-000123].
7. cited_record_ids must contain only IDs supplied in AVAILABLE RECORDS.
8. If the supplied evidence is insufficient, say so plainly in limitations.
9. Do not advise political persuasion, voter targeting, campaigning, or influence operations.
10. Keep the answer useful for an analyst: concise, evidence-grounded, and traceable.

The assistant is read-only and does not validate, verify, modify, or promote intelligence records."""

def _tokens(text):
    return [t for t in re.findall(r'[a-z0-9][a-z0-9_\-]{2,}',str(text or '').lower()) if t not in STOPWORDS]

def _record_date(item):
    for raw in (item.publication_date, item.publication_datetime):
        if raw:
            try: return datetime.fromisoformat(str(raw).replace('Z','+00:00')).date()
            except Exception: pass
    return item.created_at.date() if item.created_at else None

def _jurisdiction(item):
    if item.jurisdiction_type=='National': return 'National · Nationwide'
    return ', '.join(x for x in [item.regency_city,item.province] if x) or item.jurisdiction_type or 'Unresolved'

def _approved_values(item):
    return (human_approved_triage(item) or {}).get('values') or {}

def select_assistant_records(question, rows, limit=12):
    q=str(question or '').lower()
    tokens=_tokens(q)
    today=datetime.now(timezone.utc).date()
    wants_validated='validated' in q or 'human-approved' in q or 'human approved' in q
    wants_unverified='unverified' in q
    wants_today='today' in q or 'hari ini' in q
    wants_week='last 7 days' in q or 'past 7 days' in q or '7 hari' in q
    wants_priority='highest-priority' in q or 'highest priority' in q or 'high priority' in q or 'priority' in q

    scored=[]
    for item in rows:
        approved=_approved_values(item)
        hay=' '.join([
          item.title or '', item.original_content or '', item.province or '', item.regency_city or '',
          item.platform or '', item.author or '', item.source_name or '', json.dumps(approved,ensure_ascii=False)
        ]).lower()
        score=sum(2 for t in tokens if t in hay)
        if tokens and score==0:
            continue
        d=_record_date(item)
        if wants_validated and item.review_status=='Validated as Relevant Intelligence': score+=5
        elif wants_validated: score-=2
        if wants_unverified and item.verification_status=='UNVERIFIED': score+=5
        elif wants_unverified: score-=2
        if wants_today and d==today: score+=6
        elif wants_today: score-=3
        if wants_week and d and d>=today-timedelta(days=7): score+=5
        elif wants_week: score-=2
        if wants_priority:
            score+={'Critical':6,'High':5,'Medium':2,'Low':0}.get(item.priority,0)
        recency=(d.toordinal() if d else 0)
        scored.append((score,recency,item))

    if not scored:
        for item in rows:
            d=_record_date(item)
            scored.append((0,d.toordinal() if d else 0,item))

    scored.sort(key=lambda x:(x[0],x[1],getattr(x[2],'id',0)),reverse=True)
    return [x[2] for x in scored[:limit]]

def assistant_evidence_record(item):
    approved=human_approved_triage(item) or {}
    source,_=clean_article_text(item.original_content or '')
    return {
      'record_id':item.intelligence_id,
      'title':item.title or '',
      'publication_date':item.publication_date or '',
      'created_date':item.created_at.isoformat() if item.created_at else '',
      'confirmed_jurisdiction':_jurisdiction(item),
      'jurisdiction_confirmed':bool(item.jurisdiction_confirmed),
      'priority':item.priority or '',
      'review_status':item.review_status or '',
      'verification_status':item.verification_status or '',
      'evidence_type':item.evidence_type or '',
      'source_publisher':item.observed_publisher_handle or item.source_name or item.author or '',
      'source_excerpt':source[:1800],
      'human_approved_triage':approved.get('values') or {},
      'human_approved_field_count':approved.get('approved_count') or 0,
      'triage_review_state':approved.get('review_state') or ''
    }

def assistant_record_view(item):
    approved=human_approved_triage(item) or {}
    return {
      'id':str(item.id),
      'intelligence_id':item.intelligence_id,
      'title':item.title,
      'date':item.publication_date or (item.created_at.isoformat() if item.created_at else ''),
      'jurisdiction':_jurisdiction(item),
      'priority':item.priority,
      'review_status':item.review_status,
      'evidence_type':item.evidence_type,
      'verification_status':item.verification_status,
      'approved_count':approved.get('approved_count') or 0,
      'source_name':item.observed_publisher_handle or item.source_name or item.author or ''
    }

def _response_output_text(payload):
    if isinstance(payload.get('output_text'),str) and payload['output_text'].strip():
        return payload['output_text'].strip()
    for output in payload.get('output') or []:
        for content in output.get('content') or []:
            if content.get('type')=='output_text' and isinstance(content.get('text'),str) and content['text'].strip():
                return content['text'].strip()
            if content.get('type')=='refusal':
                raise AssistantProviderError('provider_refusal',str(content.get('refusal') or 'Model refusal')[:500])
    raise AssistantProviderError('provider_empty_output','OpenAI returned no assistant output')

def generate_openai_assistant_answer(question, previous_question, records):
    api_key=os.getenv('OPENAI_API_KEY','').strip()
    if not api_key:
        raise AssistantProviderError('not_configured','OPENAI_API_KEY is not configured')
    model=openai_triage_model()
    base_url=os.getenv('OPENAI_BASE_URL',OPENAI_DEFAULT_BASE_URL).strip().rstrip('/') or OPENAI_DEFAULT_BASE_URL
    prompt={
      'current_question':str(question or '')[:500],
      'previous_question':str(previous_question or '')[:500],
      'available_records':records
    }
    request={
      'model':model,
      'store':False,
      'input':[
        {'role':'system','content':SYSTEM_PROMPT},
        {'role':'user','content':json.dumps(prompt,ensure_ascii=False)}
      ],
      'text':{'format':{'type':'json_schema','name':'bawaslu_intelligence_assistant','strict':True,'schema':ANSWER_SCHEMA}},
      'max_output_tokens':2200
    }
    try:
        with httpx.Client(timeout=60.0) as client:
            response=client.post(base_url+'/responses',headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},json=request)
    except httpx.TimeoutException as exc:
        raise AssistantProviderError('provider_timeout','OpenAI request timed out') from exc
    except httpx.HTTPError as exc:
        raise AssistantProviderError('provider_network','OpenAI request could not be completed') from exc
    if response.status_code>=400:
        raise AssistantProviderError('provider_http_'+str(response.status_code),'OpenAI returned HTTP '+str(response.status_code))
    try: payload=response.json()
    except Exception as exc: raise AssistantProviderError('provider_bad_response','OpenAI response was not valid JSON') from exc
    if payload.get('status')=='incomplete':
        raise AssistantProviderError('provider_incomplete','OpenAI response was incomplete')
    try: result=json.loads(_response_output_text(payload))
    except AssistantProviderError: raise
    except Exception as exc: raise AssistantProviderError('provider_invalid_json','Assistant output could not be parsed') from exc
    if not isinstance(result,dict):
        raise AssistantProviderError('provider_invalid_json','Assistant output was not an object')
    usage=payload.get('usage') or {}
    meta={'mode':'OPENAI_GROUNDED','model':payload.get('model') or model,'response_id':payload.get('id') or '','usage':{'input_tokens':usage.get('input_tokens'),'output_tokens':usage.get('output_tokens'),'total_tokens':usage.get('total_tokens')}}
    return result,meta

def format_assistant_answer(result):
    def lines(values):
        return '\n'.join('- '+str(x).strip() for x in (values or []) if str(x).strip()) or '- None recorded.'
    return (
      'ANSWER / INTELLIGENCE SUMMARY\n'+str(result.get('answer_summary') or 'No supported answer could be produced.').strip()+
      '\n\nKEY OBSERVATIONS\n'+lines(result.get('key_observations'))+
      '\n\nEVIDENCE STATUS\n'+lines(result.get('evidence_status'))+
      '\n\nLIMITATION\n'+lines(result.get('limitations'))
    )

def deterministic_assistant_answer(question, records, reason=''):
    if not records:
        return {
          'answer':'ANSWER / INTELLIGENCE SUMMARY\nNo accessible intelligence records matched the question.\n\nKEY OBSERVATIONS\n- None supported by the accessible records.\n\nEVIDENCE STATUS\n- No matching record evidence was returned.\n\nLIMITATION\n- The assistant does not infer facts beyond accessible BAWASLU records.',
          'cited_record_ids':[]
        }
    ids=[r['record_id'] for r in records[:6]]
    validated=sum(1 for r in records if r.get('review_status')=='Validated as Relevant Intelligence')
    unverified=sum(1 for r in records if r.get('verification_status')=='UNVERIFIED')
    summary=f"Found {len(records)} accessible record(s) relevant to the question. {validated} are validated as relevant intelligence; {unverified} remain supported by unverified source evidence."
    observations=[f"[{r['record_id']}] {r['title']}" for r in records[:5]]
    result={
      'answer_summary':summary,
      'key_observations':observations,
      'evidence_status':[f'{validated} record(s) validated as relevant intelligence.',f'{unverified} record(s) have UNVERIFIED source evidence.'],
      'limitations':['Generative synthesis was unavailable; this is a deterministic record summary.'+(f' Provider status: {reason}.' if reason else '')],
      'cited_record_ids':ids
    }
    return {'answer':format_assistant_answer(result),'cited_record_ids':ids}
