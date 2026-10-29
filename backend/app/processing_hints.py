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

def source_hints(text):
    body=str(text or '')
    folded=body.casefold()
    topics=[name for name,terms in TOPIC_TERMS.items() if any(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',folded) for t in terms)]
    provinces=sorted({standard for alias,standard in PROVINCE_ALIASES.items()
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',folded)})
    normalized=re.sub(r'\s+',' ',folded).strip()
    return {
        'topic_suggestions':topics,
        'communication_context':communication_context(body),
        'province_mentions':provinces,
        'incident_jurisdiction_status':'UNVERIFIED',
        'province_mentions_are_incident_location':False,
        'exact_text_fingerprint':hashlib.sha256(normalized.encode('utf-8')).hexdigest() if normalized else None,
        'classification_method':'RULE_HINTS_V1',
    }
