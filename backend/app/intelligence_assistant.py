import json, os, re
from datetime import datetime, timezone, timedelta
import httpx
from .openai_triage import openai_triage_model, OPENAI_DEFAULT_BASE_URL
from .domain import human_approved_triage
from .source_retrieval import clean_article_text

class AssistantProviderError(RuntimeError):
    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code=code

STOPWORDS={
 'what','when','where','which','with','from','that','this','show','tell','about','are','the','and','for','into',
 'latest','summarise','summarize','intelligence','records','record','main','issues','highest','priority','today',
 'last','past','days','day','validated','unverified','evidence','supported','remain','remains','added','collected',
 'created','published','human-approved','human','approved','jurisdiction','jurisdictions','recent','newest','available','accessible','authorized','scope','user','users','my','our',
 'yang','dan','untuk','dari','dalam','apa','mana','terkini','ringkaskan','intelijen','catatan','rekod','bukti',
 'tervalidasi','divalidasi','belum','terverifikasi','hari','ditambahkan','dikumpulkan','dibuat','diterbitkan','tersedia','yurisdiksi','cakupan','akses','pengguna','saya','kami'
}

ANSWER_SCHEMA={
  'type':'object',
  'properties':{
    'answer_summary':{'type':'string'},
    'key_observations':{'type':'array','items':{'type':'string'},'maxItems':8},
    'evidence_status':{'type':'array','items':{'type':'string'},'maxItems':6},
    'date_basis':{'type':'string'},
    'limitations':{'type':'array','items':{'type':'string'},'maxItems':5},
    'cited_record_ids':{'type':'array','items':{'type':'string'},'maxItems':12}
  },
  'required':['answer_summary','key_observations','evidence_status','date_basis','limitations','cited_record_ids'],
  'additionalProperties':False
}

SYSTEM_PROMPT="""You are the BAWASLU Intelligence Assistant. You answer questions only from the BAWASLU intelligence records supplied in the request.

Mandatory rules:
1. The supplied records have already been restricted to the current user's authorized geographic/access scope. Never imply access to any other records.
2. Use recorded source evidence and HUMAN-APPROVED triage values only. Never treat pending, rejected, or raw AI triage suggestions as approved intelligence.
3. Clearly distinguish source reporting, human-approved analytical fields, verification status, and uncertainty.
4. UNVERIFIED evidence must remain explicitly unverified. Human relevance validation is not the same as source verification.
5. Do not invent facts, actors, relationships, violations, legal conclusions, ownership, intent, or jurisdiction.
6. Cite supporting intelligence IDs in observations using square brackets, for example [INT-2026-000123].
7. cited_record_ids must contain only IDs supplied in AVAILABLE RECORDS.
8. Respect QUERY SEMANTICS exactly, including the date_basis and time window. Do not substitute publication, collection, creation, or validation dates for one another.
9. If the supplied evidence is insufficient, say so plainly in limitations.
10. Do not advise political persuasion, voter targeting, campaigning, or influence operations.
11. Answer in clear, professional Bahasa Indonesia. Preserve proper names, source quotations, official status values, and intelligence IDs exactly where needed.
12. Avoid mixing Malay vocabulary into the analytical prose unless directly quoting the source.
13. Keep the answer useful for an analyst: concise, evidence-grounded, and traceable.

The assistant is read-only and does not validate, verify, modify, or promote intelligence records."""

def _tokens(text):
    return [t for t in re.findall(r'[a-z0-9][a-z0-9_\-]{2,}',str(text or '').lower()) if t not in STOPWORDS]

def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value,datetime):
        dt=value
    else:
        raw=str(value).strip()
        if not raw:
            return None
        try:
            dt=datetime.fromisoformat(raw.replace('Z','+00:00'))
        except Exception:
            try:
                dt=datetime.fromisoformat(raw[:10])
            except Exception:
                return None
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt

def _date(value):
    dt=_parse_datetime(value)
    return dt.date() if dt else None

def _publication_date(item):
    return _date(item.publication_datetime) or _date(item.publication_date)

def _collection_date(item):
    return _date(item.collection_datetime) or (_date(item.created_at) if item.created_at else None)

def _created_date(item):
    return _date(item.created_at) if item.created_at else None

def _validated_date(item):
    return _date(item.validated_at)

def _validated_datetime(item):
    return _parse_datetime(item.validated_at) or _parse_datetime(item.created_at)

def assistant_query_semantics(question):
    q=str(question or '').lower()
    wants_validated=('validated' in q or 'human-approved' in q or 'human approved' in q or 'tervalidasi' in q or 'divalidasi' in q)
    wants_unverified=('unverified' in q or 'belum terverifikasi' in q)
    wants_today=('today' in q or 'hari ini' in q)
    wants_week=('last 7 days' in q or 'past 7 days' in q or '7 hari' in q)
    added_context=any(x in q for x in ['added','collected','created','ditambahkan','dikumpulkan','dibuat','masuk sistem'])
    latest_context=any(x in q for x in ['latest','newest','most recent','terbaru','terkini'])

    if wants_validated and latest_context:
        basis='validated_at'
        label='Waktu validasi manusia'
        note='Diurutkan berdasarkan waktu validasi manusia (validated_at); jika timestamp validasi tidak tersedia pada data lama, waktu pembuatan dipakai hanya sebagai fallback pengurutan.'
    elif added_context and (wants_week or wants_today):
        basis='collection_or_created'
        label='Waktu pengumpulan / penambahan'
        note='Jendela waktu menggunakan waktu pengumpulan; jika tidak tersedia, waktu pembuatan record dipakai sebagai fallback.'
    elif wants_week or wants_today:
        basis='publication_date'
        label='Tanggal publikasi sumber'
        note='Jendela waktu menggunakan tanggal publikasi sumber, bukan tanggal record ditambahkan ke BAWASLU.'
    elif latest_context:
        basis='publication_date'
        label='Tanggal publikasi sumber'
        note='Urutan terbaru menggunakan tanggal publikasi sumber; record tanpa tanggal publikasi ditempatkan setelah record bertanggal.'
    else:
        basis='none'
        label='Tidak ada filter waktu khusus'
        note='Pertanyaan tidak meminta jendela atau urutan waktu khusus.'

    return {
      'date_basis':basis,
      'date_basis_label':label,
      'date_basis_note':note,
      'window':'TODAY' if wants_today else ('LAST_7_DAYS' if wants_week else 'NONE'),
      'requires_validated':wants_validated,
      'requires_unverified':wants_unverified,
      'latest':latest_context
    }

def _jurisdiction(item):
    if item.jurisdiction_type=='National': return 'National · Nationwide'
    return ', '.join(x for x in [item.regency_city,item.province] if x) or item.jurisdiction_type or 'Unresolved'

def _approved_values(item):
    return (human_approved_triage(item) or {}).get('values') or {}

def _basis_date(item,basis):
    if basis=='validated_at':
        return _validated_date(item)
    if basis=='collection_or_created':
        return _collection_date(item)
    return _publication_date(item)

def select_assistant_records(question, rows, limit=12):
    q=str(question or '').lower()
    semantics=assistant_query_semantics(q)
    tokens=_tokens(q)
    today=datetime.now(timezone.utc).date()
    start=today-timedelta(days=6)
    wants_priority=('highest-priority' in q or 'highest priority' in q or 'high priority' in q or 'priority' in q or 'prioritas' in q)

    scored=[]
    for item in rows:
        if semantics['requires_validated'] and item.review_status!='Validated as Relevant Intelligence':
            continue
        if semantics['requires_unverified'] and item.verification_status!='UNVERIFIED':
            continue

        basis_date=_basis_date(item,semantics['date_basis'])
        if semantics['window']=='TODAY' and basis_date!=today:
            continue
        if semantics['window']=='LAST_7_DAYS' and (not basis_date or basis_date<start or basis_date>today):
            continue

        approved=_approved_values(item)
        hay=' '.join([
          item.title or '', item.original_content or '', item.province or '', item.regency_city or '',
          item.platform or '', item.author or '', item.source_name or '', item.review_status or '',
          item.verification_status or '', json.dumps(approved,ensure_ascii=False)
        ]).lower()
        matched=sum(2 for t in tokens if t in hay)
        if tokens and matched==0:
            continue

        score=matched
        if semantics['requires_validated']: score+=5
        if semantics['requires_unverified']: score+=5
        if wants_priority:
            score+={'Critical':6,'High':5,'Medium':2,'Low':0}.get(item.priority,0)

        if semantics['date_basis']=='validated_at':
            dt=_validated_datetime(item)
            recency=dt.timestamp() if dt else 0
        else:
            d=basis_date or _publication_date(item) or _collection_date(item) or _created_date(item)
            recency=d.toordinal() if d else 0
        scored.append((score,recency,item))

    scored.sort(key=lambda x:(x[0],x[1],getattr(x[2],'id',0)),reverse=True)
    return [x[2] for x in scored[:limit]]

def assistant_evidence_record(item):
    approved=human_approved_triage(item) or {}
    source,_=clean_article_text(item.original_content or '')
    return {
      'record_id':item.intelligence_id,
      'title':item.title or '',
      'publication_date':item.publication_date or '',
      'publication_datetime':item.publication_datetime or '',
      'collection_datetime':item.collection_datetime or '',
      'created_at':item.created_at.isoformat() if item.created_at else '',
      'validated_at':item.validated_at or '',
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
      'publication_date':item.publication_date or '',
      'collection_datetime':item.collection_datetime or '',
      'created_at':item.created_at.isoformat() if item.created_at else '',
      'validated_at':item.validated_at or '',
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
    semantics=assistant_query_semantics(question)
    prompt={
      'current_question':str(question or '')[:500],
      'previous_question':str(previous_question or '')[:500],
      'query_semantics':semantics,
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
    if not str(result.get('date_basis') or '').strip():
        result['date_basis']=semantics['date_basis_note']
    usage=payload.get('usage') or {}
    meta={'mode':'OPENAI_GROUNDED','model':payload.get('model') or model,'response_id':payload.get('id') or '','usage':{'input_tokens':usage.get('input_tokens'),'output_tokens':usage.get('output_tokens'),'total_tokens':usage.get('total_tokens')}}
    return result,meta

def format_assistant_answer(result):
    def lines(values):
        return '\n'.join('- '+str(x).strip() for x in (values or []) if str(x).strip()) or '- Tidak ada.'
    return (
      'RINGKASAN INTELIJEN\n'+str(result.get('answer_summary') or 'Tidak ada jawaban yang dapat didukung oleh data yang tersedia.').strip()+
      '\n\nOBSERVASI KUNCI\n'+lines(result.get('key_observations'))+
      '\n\nSTATUS BUKTI\n'+lines(result.get('evidence_status'))+
      '\n\nDASAR WAKTU\n'+str(result.get('date_basis') or 'Tidak ada filter waktu khusus.').strip()+
      '\n\nKETERBATASAN\n'+lines(result.get('limitations'))
    )

def deterministic_assistant_answer(question, records, reason=''):
    semantics=assistant_query_semantics(question)
    if not records:
        return {
          'answer':(
            'RINGKASAN INTELIJEN\nTidak ada catatan intelijen yang dapat diakses dan cocok dengan pertanyaan.\n\n'
            'OBSERVASI KUNCI\n- Tidak ada observasi yang didukung oleh catatan yang tersedia.\n\n'
            'STATUS BUKTI\n- Tidak ada bukti record yang cocok untuk ditampilkan.\n\n'
            'DASAR WAKTU\n'+semantics['date_basis_note']+'\n\n'
            'KETERBATASAN\n- Asisten tidak menyimpulkan fakta di luar catatan BAWASLU yang dapat diakses.'
          ),
          'cited_record_ids':[]
        }
    ids=[r['record_id'] for r in records[:6]]
    validated=sum(1 for r in records if r.get('review_status')=='Validated as Relevant Intelligence')
    unverified=sum(1 for r in records if r.get('verification_status')=='UNVERIFIED')
    result={
      'answer_summary':f'Ditemukan {len(records)} catatan intelijen yang dapat diakses dan relevan dengan pertanyaan. {validated} telah divalidasi sebagai intelijen relevan; {unverified} masih didukung oleh sumber berstatus UNVERIFIED.',
      'key_observations':[f"[{r['record_id']}] {r['title']}" for r in records[:5]],
      'evidence_status':[f'{validated} catatan berstatus Validated as Relevant Intelligence.',f'{unverified} catatan memiliki sumber berstatus UNVERIFIED.'],
      'date_basis':semantics['date_basis_note'],
      'limitations':['Sintesis generatif tidak tersedia; jawaban ini adalah ringkasan deterministik dari catatan yang terpilih.'+(f' Status provider: {reason}.' if reason else '')],
      'cited_record_ids':ids
    }
    return {'answer':format_assistant_answer(result),'cited_record_ids':ids}
