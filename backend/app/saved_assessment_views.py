"""Read-only, role-scoped reuse of actual saved campaign classifications.

No provider calls. Smart Radar's pilot-specific source IDs are intentionally not
joined to Social Listening IDs without explicit persisted source lineage.
"""
import json
from .access import allowed, has
from .models import (CampaignEvidence, MonitoringCampaign, EvidenceAssessment,
                     EvidenceReview, IssueCategory, IssueCategoryPhrase)
from .issue_signals import validated_issue_signals, phrase_screening_candidates
from .source_ids import canonical_source_id

RELEVANT={'RELEVANT','HIGHLY_RELEVANT'}
REVIEW_DECISIONS={'FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION'}


def saved_classifications_for_posts(db, user_profile, posts):
    """Return latest saved, relevant classifications for an already scoped page.

    Links and campaign authorization are checked again here to prevent a
    watchlist account from revealing private campaign decisions. Never promote
    text-only keyword leads to saved AI signals.
    """
    result={post.id:[] for post in posts}
    if not result or not has(user_profile,'view_intelligence'):
        return result
    ids=set(result)
    links=db.query(CampaignEvidence).filter(CampaignEvidence.result_id.in_(ids)).all()
    campaigns={cid:db.get(MonitoringCampaign,cid)
               for cid in {link.campaign_id for link in links}}
    permitted={(link.campaign_id,link.result_id) for link in links
               if campaigns.get(link.campaign_id) and
               allowed(user_profile,campaigns[link.campaign_id])}
    if not permitted:
        return result
    campaign_ids={cid for cid,_ in permitted}
    assessments=(db.query(EvidenceAssessment)
        .filter(EvidenceAssessment.campaign_id.in_(campaign_ids),
                EvidenceAssessment.result_id.in_(ids))
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).all())
    latest={}
    for assessment in assessments:
        key=(assessment.campaign_id,assessment.result_id)
        if key in permitted and key not in latest:
            latest[key]=assessment
    relevant={key:item for key,item in latest.items()
              if str(item.relevance_label or '').upper() in RELEVANT}
    if not relevant:
        return result

    categories=db.query(IssueCategory).filter(IssueCategory.active==True).all()
    taxonomy={category.id:category.name for category in categories}
    phrases=db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.active==True).all()
    reviews=(db.query(EvidenceReview,EvidenceAssessment.campaign_id,
                      EvidenceAssessment.result_id)
        .join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
        .filter(EvidenceAssessment.campaign_id.in_(campaign_ids),
                EvidenceAssessment.result_id.in_(ids),
                EvidenceReview.decision.in_(REVIEW_DECISIONS))
        .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).all())
    decisions={}
    for review,campaign_id,result_id in reviews:
        key=(campaign_id,result_id)
        if key in relevant and key not in decisions:
            decisions[key]=review.decision
    from .candidate_registry import candidate_index, resolve_signals
    scoped_candidate_index=candidate_index(db,user_profile)
    posts_by_id={post.id:post for post in posts}
    for (campaign_id,result_id),assessment in sorted(relevant.items()):
        post=posts_by_id[result_id]
        try:
            raw=json.loads(assessment.potential_issue_signals_json or '[]')
        except (ValueError,TypeError):
            raw=[]
        if not isinstance(raw,list):
            raw=[]
        signals=validated_issue_signals(raw,taxonomy,post.text_content)
        source='SAVED_ASSESSMENT' if signals else 'NO_VALID_SAVED_SIGNAL'
        if not signals:
            signals=phrase_screening_candidates(post.text_content,categories,phrases)
            if signals:source='KEYWORD_REVIEW_LEAD'
        decision=decisions.get((campaign_id,result_id))
        from .jurisdiction_review import jurisdiction_status
        location_review=jurisdiction_status(db,campaign_id,result_id,post)
        dismissed=decision=='FLAG_DISMISSED'
        result[result_id].append({
            'canonical_source_id':canonical_source_id('social',result_id),
            'campaign_id':str(campaign_id),
            'campaign_name':campaigns[campaign_id].name,
            'assessment_version':assessment.assessment_version,
            'model_version':assessment.model_version,
            'relevance_label':assessment.relevance_label,
            'sentiment':str(assessment.sentiment or 'UNCLASSIFIED').upper(),
            'sentiment_confidence':assessment.sentiment_confidence or '',
            'sentiment_explanation':assessment.sentiment_explanation or '',
            'sentiment_model':assessment.sentiment_model or '',
            'candidate_identity_matches':resolve_signals(
                _safe_candidate_signals(assessment.candidate_signals_json),
                scoped_candidate_index),
            'incident_jurisdiction_review':location_review,
            'topic_labels':_safe_candidate_signals(assessment.topic_labels_json),
            'public_concern_signals':_safe_candidate_signals(assessment.public_concern_signals_json),
            'attention_assessment':_safe_object(assessment.attention_assessment_json),
            'player_summary_drafts':_safe_candidate_signals(assessment.player_summaries_json),
            'potential_issues':signals,
            'signal_source':source,
            'review_status':decision,
            'is_flagged':not dismissed and (
                (source=='SAVED_ASSESSMENT' and bool(signals)) or
                decision in ('FLAG_CONFIRMED','FURTHER_INVESTIGATION')),
            'human_validation_required':True,
            'assessment_persisted':True,
        })
    return result

def _safe_candidate_signals(raw):
    try:
        value=json.loads(raw or '[]')
    except (TypeError,ValueError):
        return []
    return value if isinstance(value,list) else []

def _safe_object(raw):
    try:
        value=json.loads(raw or '{}')
    except (TypeError,ValueError):
        return {}
    return value if isinstance(value,dict) else {}
