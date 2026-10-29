"""Permission-scoped, human-validated incident jurisdiction.

No profile-location inference, no model calls, and no automatic ACL expansion.
"""
import hashlib
import re
from datetime import datetime
from .access import allowed, has, audit
from .models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
                     EvidenceAssessment,CampaignJurisdictionReview)
from .socialcrawl import _result_in_scope
from .processing_hints import incident_location_cues


def fingerprint(text):
    return hashlib.sha256(re.sub(r'\s+',' ',str(text or '').casefold()).strip().encode()).hexdigest()


def scoped_post(db,p,campaign_id,result_id):
    if not str(campaign_id or '').isdigit() or not str(result_id or '').isdigit():
        raise ValueError('Valid campaign and source post IDs required')
    campaign=db.get(MonitoringCampaign,int(campaign_id))
    if not campaign or not allowed(p,campaign):
        raise PermissionError('Campaign unavailable')
    link=db.query(CampaignEvidence).filter_by(
        campaign_id=campaign.id,result_id=int(result_id)).first()
    post=db.get(SocialListeningResult,int(result_id))
    if not link or not post or not _result_in_scope(db,p,post):
        raise PermissionError('Source post unavailable')
    assessment=db.query(EvidenceAssessment).filter_by(
        campaign_id=campaign.id,result_id=post.id).order_by(
        EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc()).first()
    relevant=bool(assessment and str(assessment.relevance_label or '').upper()
                  in ('RELEVANT','HIGHLY_RELEVANT'))
    return campaign,post,relevant


def jurisdiction_status(db,campaign_id,result_id,post):
    row=db.query(CampaignJurisdictionReview).filter_by(
        campaign_id=int(campaign_id),result_id=int(result_id)).first()
    if not row:return {'decision':'UNREVIEWED','incident_jurisdiction_verified':False}
    current=fingerprint(post.text_content)
    if current!=row.evidence_fingerprint:
        return {'decision':'STALE_SOURCE_CHANGED',
                'incident_jurisdiction_verified':False}
    verified=row.decision=='CONFIRMED'
    if verified:
        latest=(db.query(EvidenceAssessment).filter_by(
            campaign_id=int(campaign_id),result_id=int(result_id))
            .order_by(EvidenceAssessment.assessment_version.desc(),
                      EvidenceAssessment.id.desc()).first())
        if not latest or str(latest.relevance_label or '').upper() not in (
                'RELEVANT','HIGHLY_RELEVANT'):
            return {'decision':'STALE_RELEVANCE_CHANGED',
                    'incident_jurisdiction_verified':False}
    return {'decision':row.decision,
        'incident_province':row.province if verified else None,
        'incident_jurisdiction_verified':verified,
        'human_review_rationale':row.rationale,
        'reviewed_by':row.reviewer_id}


def jurisdiction_action(db,p,action,data,id=None):
    if not has(p,'view_intelligence'):
        raise PermissionError('Intelligence access required')
    campaign,post,relevant=scoped_post(
        db,p,id or data.get('campaign_id'),data.get('result_id'))
    locations=incident_location_cues(post.text_content)
    status=jurisdiction_status(db,campaign.id,post.id,post)
    preview={'campaign_id':str(campaign.id),'result_id':str(post.id),
        'canonical_source_id':'social:'+str(post.id),
        'source_context_provinces_unverified':locations,
        'source_post_relevance_assessed':relevant,
        'source_evidence_verified':False,
        'geographic_acl_expanded':False,
        'latest_review':status,
        'paid_provider_called':False}
    if action=='campaignJurisdictionPreview':return preview
    if action!='campaignJurisdictionReview':
        raise ValueError('Unknown jurisdiction action')
    if not has(p,'human_validation'):
        raise PermissionError('Human Validation permission required')
    if not relevant:
        raise ValueError('Relevant saved assessment required before jurisdiction verification')
    decision=str(data.get('decision') or '')
    if decision not in ('CONFIRMED','REJECTED'):
        raise ValueError('Choose CONFIRMED or REJECTED')
    province=str(data.get('province') or '')
    if decision=='CONFIRMED' and (len(locations)!=1 or province!=locations[0]):
        raise ValueError('Cannot confirm an ambiguous or unsupported incident province')
    if decision=='REJECTED':
        province=''
    rationale=' '.join(str(data.get('rationale') or '').split())
    if not 10<=len(rationale)<=1200:
        raise ValueError('Human review rationale must contain 10-1200 characters')
    row=db.query(CampaignJurisdictionReview).filter_by(
        campaign_id=campaign.id,result_id=post.id).first()
    if row is None:
        row=CampaignJurisdictionReview(campaign_id=campaign.id,result_id=post.id)
        db.add(row)
    row.province=province
    row.evidence_fingerprint=fingerprint(post.text_content)
    row.decision=decision
    row.rationale=rationale
    row.reviewer_id=str(p.get('id') or '')
    row.reviewed_at=datetime.utcnow()
    db.commit()
    audit(db,p,'CampaignJurisdictionReview',row.id,'INCIDENT_JURISDICTION_REVIEWED',
        {'campaign_id':campaign.id,'result_id':post.id,'decision':decision,
         'province':province,'geographic_acl_expanded':False})
    return {**preview,'saved':True,
        'latest_review':jurisdiction_status(db,campaign.id,post.id,post)}
