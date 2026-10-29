"""Officer-signed topic and public-concern corrections; append-only assessment lineage."""
import json
from .access import allowed, has, audit
from .models import (MonitoringCampaign, CampaignEvidence, SocialListeningResult,
                     EvidenceAssessment, EvidenceReview)
from .socialcrawl import _result_in_scope

ALLOWED_TOPICS={'Electoral Operations','BAWASLU Reputation'}
def correct_classification(db,p,campaign_id,payload):
    if not (has(p,'human_validation') and has(p,'review_ai_suggestions')):
        raise PermissionError('Human validation and AI review permissions required')
    if not str(campaign_id or '').isdigit():raise ValueError('Select a campaign')
    payload=payload if isinstance(payload,dict) else {}
    result_id=str(payload.get('result_id') or '')
    if not result_id.isdigit():raise ValueError('Invalid source post ID')
    campaign=db.get(MonitoringCampaign,int(campaign_id))
    if not campaign or not allowed(p,campaign):raise PermissionError('Campaign not available')
    link=db.query(CampaignEvidence).filter_by(campaign_id=campaign.id,result_id=int(result_id)).first()
    post=db.get(SocialListeningResult,int(result_id))
    if not link or not post or not _result_in_scope(db,p,post):
        raise PermissionError('Source evidence unavailable in officer scope')
    old=(db.query(EvidenceAssessment).filter_by(campaign_id=campaign.id,result_id=post.id)
         .order_by(EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc())
         .with_for_update().first())
    if not old:raise ValueError('Saved assessment required')
    try:expected=int(payload.get('expected_version'))
    except (ValueError,TypeError):raise ValueError('Assessment version required') from None
    if expected!=old.assessment_version:raise ValueError('Assessment changed; refresh before correction')
    rationale=str(payload.get('rationale') or '').strip()
    if not 15<=len(rationale)<=1500:raise ValueError('Provide 15–1500 characters of officer rationale')
    mode=payload.get('correction_type')
    if mode=='TOPICS':
        topics=payload.get('topics')
        if not isinstance(topics,list) or any(x not in ALLOWED_TOPICS for x in topics):
            raise ValueError('Invalid topic selection')
        topics=sorted(set(topics))
        if str(old.relevance_label or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT') and topics:
            raise ValueError('Cannot assign topics to an irrelevant/unassessed post')
        topic_json=json.dumps(topics)
        concern_json=old.public_concern_signals_json
        decision='TOPIC_CORRECTED'
    elif mode=='PUBLIC_CONCERN':
        quote=str(payload.get('source_quote') or '').strip()
        concern=str(payload.get('concern') or '').strip()
        if not 10<=len(concern)<=240:raise ValueError('Explain the public concern')
        if str(old.relevance_label or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
            raise ValueError('Post must have saved relevant classification')
        if len(quote)<15 or quote.casefold() not in str(post.text_content or '').casefold():
            raise ValueError('Verbatim source quotation of at least 15 characters required')
        # Unlike AI classification, an authorized officer can attest an explicit
        # complaint without a brittle keyword heuristic. It remains an
        # unverified public concern, not a legal finding.
        normalized=[{'evidence_quote':quote,'concern':concern,
                     'status':'HUMAN_CONCERN_REVIEWED',
                     'provenance':'OFFICER_SOURCE_REVIEW',
                     'legal_violation_confirmed':False}]
        concerns=json.loads(old.public_concern_signals_json or '[]')
        if not isinstance(concerns,list):concerns=[]
        if any(x.get('evidence_quote')==quote for x in concerns if isinstance(x,dict)):
            raise ValueError('This source quotation is already recorded')
        concern_json=json.dumps(concerns+[normalized[0]],ensure_ascii=False)
        topic_json=old.topic_labels_json
        decision='PUBLIC_CONCERN_REVIEWED'
    else:raise ValueError('Select topic correction or public concern review')
    if topic_json==old.topic_labels_json and concern_json==old.public_concern_signals_json:
        raise ValueError('No change to save')
    new=EvidenceAssessment(campaign_id=campaign.id,result_id=post.id,
        assessment_version=old.assessment_version+1,model_version='HUMAN_CLASSIFICATION_REVIEW',
        relevance_label=old.relevance_label,relevance_confidence=old.relevance_confidence,
        sentiment=old.sentiment,sentiment_confidence=old.sentiment_confidence,
        sentiment_explanation=old.sentiment_explanation,sentiment_model=old.sentiment_model,
        candidate_signals_json=old.candidate_signals_json,
        geographic_signals_json=old.geographic_signals_json,
        potential_issue_signals_json=old.potential_issue_signals_json,
        topic_labels_json=topic_json,public_concern_signals_json=concern_json,
        attention_assessment_json=old.attention_assessment_json,
        player_summaries_json=old.player_summaries_json,
        explanation='Officer classification review: '+rationale)
    db.add(new);db.flush()
    db.add(EvidenceReview(assessment_id=new.id,reviewer_id=str(p['id']),
                          decision=decision,rationale=rationale))
    db.commit()
    audit(db,p,'EvidenceAssessment',new.id,'HUMAN_CLASSIFICATION_REVIEW',{
        'previous_assessment_id':old.id,'result_id':post.id,'campaign_id':campaign.id,
        'correction_type':mode,'decision':decision})
    return {'saved':True,'assessment_version':new.assessment_version,
            'correction_type':mode,'paid_provider_called':False}
