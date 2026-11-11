"""Saved, source-grounded sentiment annotation validation.

Sentiment describes the explicitly expressed tone toward the subject. It is
not political support, a legal violation finding, or inferred intent.
"""
VALID_SENTIMENT={'POSITIVE','NEUTRAL','NEGATIVE','UNCLASSIFIED'}
VALID_CONFIDENCE={'LOW','MEDIUM','HIGH'}

def normalize_sentiment_output(output):
    """Fail closed on absent/malformed provider output, never invent a label."""
    if not isinstance(output,dict):
        output={}
    label=output.get('sentiment')
    valid=isinstance(label,str) and label.strip().upper() in VALID_SENTIMENT
    label=label.strip().upper() if valid else 'UNCLASSIFIED'
    confidence=output.get('sentiment_confidence')
    confidence=confidence.strip().upper() if isinstance(confidence,str) else ''
    if confidence not in VALID_CONFIDENCE:
        confidence='LOW'
    if label=='UNCLASSIFIED':
        confidence='LOW'
    reason=output.get('sentiment_explanation')
    reason=reason.strip()[:400] if isinstance(reason,str) else ''
    if not reason:
        reason='Insufficient source text to determine the expressed sentiment.' if label=='UNCLASSIFIED' else 'AI explanation not supplied; requires review.'
    return {'sentiment':label,'sentiment_confidence':confidence,
            'sentiment_explanation':reason,'valid':valid}

def sentiment_is_assessed(record):
    """UNCLASSIFIED may be the result of a *completed* assessment."""
    if not record:return False
    label=str(getattr(record,'sentiment','') or '').strip().upper()
    model=str(getattr(record,'sentiment_model','') or '').strip()
    # Legacy Prism rows used the provider model name even when the provider's
    # stance.label was null. No classification occurred in that case.
    if label=='UNCLASSIFIED' and model=='socialcrawl-prism-stance':
        return False
    return bool(model) or label in ('POSITIVE','NEUTRAL','NEGATIVE')

def relevance_is_assessed(record):
    """Sentiment-only annotations must not suppress the main AI assessment."""
    return bool(record and str(getattr(record,'relevance_label','') or '').upper()
                in ('RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN'))


def latest_saved_sentiments(db,campaign_id):
    """One campaign-scoped saved-truth read, including officer overrides.

    Sentiment assessment status is independent of topic-classification status.
    A missing provider stance is pending; a completed uncertain AI assessment
    remains Unclassified. No paid inference or per-post lookups occur here.
    """
    from .models import EvidenceAssessment
    from .officer_sentiment import OfficerSentimentCorrection
    latest={}
    rows=(db.query(EvidenceAssessment.result_id,EvidenceAssessment.sentiment,
                   EvidenceAssessment.sentiment_model)
          .filter(EvidenceAssessment.campaign_id==int(campaign_id))
          .order_by(EvidenceAssessment.assessment_version.desc(),
                    EvidenceAssessment.id.desc()).yield_per(1000))
    for result_id,label,model in rows:
        if result_id in latest:continue
        raw=str(label or '').strip().upper()
        if raw in ('POSITIVE','NEUTRAL','NEGATIVE'):
            latest[result_id]=raw.title()
        elif sentiment_is_assessed(type('SavedTone',(),{'sentiment':raw,
                                                       'sentiment_model':model})()):
            latest[result_id]='Unclassified'
        else:
            latest[result_id]='Pending assessment'
    # Officer decisions always win; one bounded query, not N+1 post lookups.
    corrections=(db.query(OfficerSentimentCorrection.result_id,
                          OfficerSentimentCorrection.sentiment)
                 .filter(OfficerSentimentCorrection.campaign_id==int(campaign_id))
                 .order_by(OfficerSentimentCorrection.id.desc()).yield_per(1000))
    overridden=set()
    for result_id,label in corrections:
        if result_id not in overridden:
            latest[result_id]=str(label).strip().title()
            overridden.add(result_id)
    return latest
