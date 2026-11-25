"""Read-only saved-post facets; source mentions are not confirmed jurisdiction."""
import json,re
from collections import Counter
from .processing_hints import normalize_candidate_signals
from .inbox_provinces import matching_source_provinces
from .incident_regency_candidates import incident_regency_preview
from .geography import INDONESIAN_PROVINCE_ALIASES
FIELDS=('platform','sentiment','province','regency','topic','candidate','author','content_type','language','relevance','assessment','issue','concern','location_confidence')
METRICS=('engagement_total','likes','comments','shares','views')
def values(value):
    if value is None or value=='':return []
    if isinstance(value,str):value=[value]
    if not isinstance(value,list) or len(value)>50 or any(not isinstance(x,str) or len(x)>255 for x in value):
        raise ValueError('Invalid saved post filter')
    return list(dict.fromkeys(x.strip() for x in value if x.strip()))
def parse_filters(spec):
    out={k:values(spec.get(k)) for k in FIELDS}
    for k in METRICS:
        for suffix in ('min','max'):
            key=k+'_'+suffix
            val=spec.get(key)
            if val is not None and val!='':
                if type(val) is not int or not 0<=val<10**15:raise ValueError('Invalid engagement range')
                out[key]=val
        if k+'_min' in out and k+'_max' in out and out[k+'_min']>out[k+'_max']:
            raise ValueError('Minimum engagement must not exceed maximum')
    return out
def labels(raw):
    try:items=json.loads(raw or '[]')
    except (TypeError,ValueError):return []
    if not isinstance(items,list):return []
    out=[]
    for item in items:
        val=item if isinstance(item,str) else next((item.get(k) for k in ('label','name','topic','category','issue_type','issue','concern','value','type') if isinstance(item.get(k),str) and item.get(k)),None) if isinstance(item,dict) else None
        if val and val.strip():out.append(val.strip()[:255])
    return list(dict.fromkeys(out))
def metadata(row,metrics,verified=None,geography=False):
    content,author,handle,platform,kind,lang,eng,model,relevance,topics,candidates,signals,issues,concerns,job,correction,sentiment=row
    complete=bool(relevance and str(relevance).upper() in ('RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN') and str(model or '').upper() not in ('PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER'))
    sentiment=str(correction or sentiment or '').lower()
    if sentiment not in ('positive','neutral','negative'):sentiment='unclassified'
    province=[];regency=[]
    if geography:
        province=matching_source_provinces(content,signals)
        for item in incident_regency_preview(content).get('candidates',[]):
            name=item.get('regency_city');pcode=item.get('province_code')
            p=INDONESIAN_PROVINCE_ALIASES.get(pcode,[item.get('province') or ''])[0]
            if name and p:
                regency.append(p+' | '+name);province.append(p)
    verified=verified or {}
    city=verified.get('regency_city_review') or {}
    if city.get('incident_regency_city_verified'):
        p=city.get('incident_province');name=city.get('incident_regency_city')
        if p and name:province.append(p);regency.append(p+' | '+name)
    if verified.get('incident_jurisdiction_verified') and verified.get('incident_province'):province.append(verified['incident_province'])
    loc='verified' if verified.get('incident_jurisdiction_verified') or city.get('incident_regency_city_verified') else 'mentioned' if province else 'unknown'
    state='assessed' if complete else 'failed' if job=='FAILED' else 'processing' if job=='PROCESSING' else 'pending'
    verified_provinces=[];verified_regencies=[]
    if verified.get('incident_jurisdiction_verified') and verified.get('incident_province'):verified_provinces.append(verified['incident_province'])
    if city.get('incident_regency_city_verified') and city.get('incident_province') and city.get('incident_regency_city'):
        verified_provinces.append(city['incident_province']);verified_regencies.append(city['incident_province']+' | '+city['incident_regency_city'])
    return {'platform':[platform] if platform else [],'sentiment':[sentiment],
        'verified_provinces':verified_provinces,'verified_regencies':verified_regencies,
        'province':list(dict.fromkeys(province)) or ['Unknown'],'regency':list(dict.fromkeys(regency)),
        'topic':labels(topics),'candidate':normalize_candidate_signals(labels(candidates)),
        'author':list(dict.fromkeys(x for x in (author,handle) if x)),
        'content_type':[kind] if kind else [],'language':[lang] if lang else ['Unknown'],
        'relevance':[str(relevance).lower() if complete else 'pending'],
        'assessment':[state]+(['officer_corrected'] if correction else []),
        'issue':labels(issues),'concern':labels(concerns),'location_confidence':[loc],
        'metrics':metrics(eng),'hashtags':list(dict.fromkeys(re.findall(r'#[\w]+',str(content or ''))))[:30]}
def matches(meta,filters):
    verified_only={x.casefold() for x in filters['location_confidence']}=={'verified'}
    for key in FIELDS:
        actual=meta['verified_provinces'] if verified_only and key=='province' else meta['verified_regencies'] if verified_only and key=='regency' else meta[key]
        if filters.get(key) and not {x.casefold() for x in filters[key]} & {str(x).casefold() for x in actual}:return False
    for k,v in filters.items():
        if k.endswith(('_min','_max')):
            metric=meta['metrics'].get(k[:-4])
            if metric is None or (k.endswith('_min') and metric<v) or (k.endswith('_max') and metric>v):return False
    return True
def accumulate(counters,meta):
    for k,counter in counters.items():
        for val in set(meta.get(k,[])):
            if val and (val in counter or len(counter)<5000):counter[val]+=1
def facet_payload(counters):
    return {k:[{'value':v,'count':n} for v,n in counter.most_common(100)] for k,counter in counters.items()}
def new_counters():
    return {k:Counter() for k in (*FIELDS,'hashtags')}
