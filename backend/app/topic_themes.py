"""V10 categorical themes, based exclusively on saved AI annotations."""
import json
from .models import EvidenceAssessment
CATEGORIES=('Public Information','Voter Registration','Electoral Operations','Campaign Rules','Public Concern','BAWASLU Reputation')
UNCATEGORIZED='Not categorized'
def _list(value):
    try: parsed=value if isinstance(value,list) else json.loads(value or '[]')
    except (ValueError,TypeError): return []
    return parsed if isinstance(parsed,list) else []
def category_for_assessment(relevance,topics,concerns):
    if str(relevance or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):return UNCATEGORIZED
    # Future assessment outputs have one primary topic, old records may have more.
    for topic in _list(topics):
        if isinstance(topic,str) and topic in CATEGORIES:return topic
    if any(isinstance(c,dict) and c.get('evidence_quote') for c in _list(concerns)):return 'Public Concern'
    return UNCATEGORIZED
def latest_saved_categories(db,campaign_id):
    rows=(db.query(EvidenceAssessment.result_id,EvidenceAssessment.relevance_label,EvidenceAssessment.topic_labels_json,EvidenceAssessment.public_concern_signals_json)
          .filter(EvidenceAssessment.campaign_id==int(campaign_id))
          .order_by(EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc()).yield_per(1000))
    result={}
    for source_id,relevance,topics,concerns in rows:
        if source_id not in result:result[source_id]=category_for_assessment(relevance,topics,concerns)
    return result
