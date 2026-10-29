"""Read-only conservative topic-quality audit. Flags for review; never rewrites assessments."""
import re
from .classification_enrichment import json_list

def topic_quality_flags(source, topic_labels):
    labels=json_list(topic_labels)
    body=str(source or '')
    content=re.sub(r'https?://\\S+|#[\\w_]+|@[\\w_.]+',' ',body.lower(),flags=re.I)
    content=re.sub(r'\\s+',' ',content).strip()
    flags=[]
    if labels and len(content)<24:
        flags.append('INSUFFICIENT_NON_HASHTAG_CONTEXT')
    if 'BAWASLU Reputation' in labels:
        reputation_terms=('kepercayaan','netral','integritas','kecurangan',
           'bertanggung jawab','reputasi','kritik','buruk','bohong','bohongnya',
           'kebohongan','pelanggaran','tidak percaya','ketidakpercayaan')
        if not ('bawaslu' in content and any(t in content for t in reputation_terms)):
            flags.append('REPUTATION_LABEL_REQUIRES_SOURCE_REVIEW')
    if 'Electoral Operations' in labels:
        ops_terms=('pemilu','pilkada','pemilihan','pengawasan','pengawas',
            'pilpres','pileg','pencoblos','mencoblos','kpu','tps','rekapitulasi',
            'kampanye','sosialisasi','sirekap','silon','caleg','suara',
            'panwas','pencalonan')
        if not any(t in content for t in ops_terms):
            flags.append('ELECTORAL_LABEL_REQUIRES_SOURCE_REVIEW')
    return flags
