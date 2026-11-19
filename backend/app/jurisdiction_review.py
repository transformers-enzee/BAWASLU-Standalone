"""Permission-scoped, human-validated incident jurisdiction.

No profile-location inference, no model calls, and no automatic ACL expansion.
"""
import hashlib
import json
import re
from datetime import datetime
from .access import allowed, has, audit
from .models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
                     EvidenceAssessment,CampaignJurisdictionReview,AuditEvent)
from .socialcrawl import _result_in_scope
from .processing_hints import incident_location_cues
from .incident_regency_candidates import incident_regency_preview
from .related_incident_locations import related_regency_mentions
from .geography import INDONESIAN_PROVINCE_ALIASES


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


def regency_review_history(db,campaign_id,result_id,limit=12):
    """Bounded immutable decisions; callers must pass scoped_post first."""
    events=(db.query(AuditEvent).filter_by(
        subject_type='CampaignIncidentRegencyReview',
        subject_id=f'{int(campaign_id)}:{int(result_id)}',
        action='INCIDENT_REGENCY_REVIEWED')
        .order_by(AuditEvent.id.desc()).limit(limit).all())
    history=[]
    for event in events:
        try:
            data=json.loads(event.changes_json or '{}')
        except (TypeError,ValueError):
            data={}
        history.append({
            'event_id':event.id,
            'decision':str(data.get('decision') or 'UNKNOWN'),
            'regency_city':str(data.get('regency_city') or ''),
            'regency_city_code':str(data.get('regency_city_code') or ''),
            'province':str(data.get('province') or ''),
            'reviewed_by':event.actor_id,
            'reviewed_at_utc':event.occurred_at,
            'rationale':str(data.get('rationale') or ''),
            'historical_decision_not_current_verification':True,
        })
    return {'history':history,'history_limit':limit,
            'history_may_be_truncated':len(history)==limit,
            'audit_events_are_not_current_verification':True,
            'read_only':True}


def regency_review_status(db,campaign_id,result_id,post):
    """Read the last append-only officer decision; never infer verification."""
    event=(db.query(AuditEvent).filter_by(
        subject_type='CampaignIncidentRegencyReview',
        subject_id=f'{int(campaign_id)}:{int(result_id)}',
        action='INCIDENT_REGENCY_REVIEWED')
        .order_by(AuditEvent.id.desc()).first())
    if not event:
        return {'decision':'UNREVIEWED','incident_regency_city_verified':False,
                'review_event_id':0}
    try:
        data=json.loads(event.changes_json or '{}')
    except (TypeError,ValueError):
        data={}
    verified=data.get('decision')=='CONFIRMED'
    status={'decision':str(data.get('decision') or 'UNREVIEWED'),
            'incident_regency_city_verified':False,
            'review_event_id':event.id,
            'reviewed_by':event.actor_id}
    if data.get('evidence_fingerprint')!=fingerprint(post.text_content):
        status['decision']='STALE_SOURCE_CHANGED'
        return status
    if verified:
        latest=(db.query(EvidenceAssessment).filter_by(
            campaign_id=int(campaign_id),result_id=int(result_id))
            .order_by(EvidenceAssessment.assessment_version.desc(),
                      EvidenceAssessment.id.desc()).first())
        if not latest or str(latest.relevance_label or '').upper() not in (
                'RELEVANT','HIGHLY_RELEVANT'):
            status['decision']='STALE_RELEVANCE_CHANGED'
            return status
        # A newer version of the saved assessment must not silently reuse
        # an older officer conclusion, even if its relevance stayed the same.
        if latest.assessment_version!=data.get('assessment_version'):
            status['decision']='STALE_ASSESSMENT_CHANGED'
            return status
    if verified:
        province_row=db.query(CampaignJurisdictionReview).filter_by(
            campaign_id=int(campaign_id),result_id=int(result_id)).first()
        if province_row and province_row.decision in ('CONFIRMED','REJECTED'):
            province_current=fingerprint(post.text_content)==province_row.evidence_fingerprint
            if province_current:
                confirmed_city_province=str(data.get('province') or '')
                if (province_row.decision=='REJECTED' or
                        province_row.province!=confirmed_city_province):
                    status['decision']='PROVINCE_REVIEW_CONFLICT'
                    return status
    status.update({'incident_regency_city_verified':verified,
        'incident_regency_city':data.get('regency_city') if verified else None,
        'incident_regency_city_code':data.get('regency_city_code') if verified else None,
        'incident_province':data.get('province') if verified else None,
        'human_review_rationale':data.get('rationale')})
    return status


def jurisdiction_status(db,campaign_id,result_id,post):
    row=db.query(CampaignJurisdictionReview).filter_by(
        campaign_id=int(campaign_id),result_id=int(result_id)).first()
    province_status={'decision':'UNREVIEWED','incident_jurisdiction_verified':False}
    if row:
        current=fingerprint(post.text_content)
        if current!=row.evidence_fingerprint:
            province_status={'decision':'STALE_SOURCE_CHANGED',
                'incident_jurisdiction_verified':False}
        else:
            verified=row.decision=='CONFIRMED'
            if verified:
                latest=(db.query(EvidenceAssessment).filter_by(
                    campaign_id=int(campaign_id),result_id=int(result_id))
                    .order_by(EvidenceAssessment.assessment_version.desc(),
                              EvidenceAssessment.id.desc()).first())
                if not latest or str(latest.relevance_label or '').upper() not in (
                        'RELEVANT','HIGHLY_RELEVANT'):
                    province_status={'decision':'STALE_RELEVANCE_CHANGED',
                        'incident_jurisdiction_verified':False}
                else:
                    province_status={'decision':row.decision,
                        'incident_province':row.province,
                        'incident_jurisdiction_verified':True,
                        'human_review_rationale':row.rationale,
                        'reviewed_by':row.reviewer_id}
            else:
                province_status={'decision':row.decision,
                    'incident_province':None,
                    'incident_jurisdiction_verified':False,
                    'human_review_rationale':row.rationale,
                    'reviewed_by':row.reviewer_id}
    province_status['regency_city_review']=regency_review_status(
        db,campaign_id,result_id,post)
    return province_status


def save_regency_review(db,p,campaign,post,relevant,data,province_status):
    if not has(p,'human_validation'):
        raise PermissionError('Human Validation permission required')
    if not relevant:
        raise ValueError('Relevant saved assessment required for city review')
    if str(data.get('expected_source_fingerprint') or '')!=fingerprint(post.text_content):
        raise ValueError('Source changed since preview; refresh before reviewing')
    # PostgreSQL row lock serializes concurrent review writes for this
    # campaign. Re-read the latest decision only after acquiring the lock.
    # SQLite ignores FOR UPDATE but local regression verifies sequential CAS.
    db.query(MonitoringCampaign).filter_by(id=campaign.id).with_for_update().first()
    current=regency_review_status(db,campaign.id,post.id,post)
    try:
        expected=int(data.get('expected_review_event_id',-1))
    except (TypeError,ValueError):
        raise ValueError('Invalid review revision')
    if expected!=current['review_event_id']:
        raise ValueError('Review changed since preview; refresh before reviewing')
    decision=str(data.get('decision') or '')
    if decision not in ('CONFIRMED','REJECTED'):
        raise ValueError('Choose CONFIRMED or REJECTED')
    rationale=' '.join(str(data.get('rationale') or '').split())
    if not 10<=len(rationale)<=1200:
        raise ValueError('Human review rationale must contain 10-1200 characters')
    latest=(db.query(EvidenceAssessment).filter_by(
        campaign_id=campaign.id,result_id=post.id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).first())
    if not latest or str(latest.relevance_label or '').upper() not in (
            'RELEVANT','HIGHLY_RELEVANT'):
        raise ValueError('Current saved assessment is not relevant')
    try:
        expected_assessment=int(data.get('expected_assessment_version',-1))
    except (TypeError,ValueError):
        raise ValueError('Invalid expected assessment version')
    if expected_assessment!=latest.assessment_version:
        raise ValueError('Saved assessment changed since preview; refresh before reviewing')
    candidates=incident_regency_preview(post.text_content)['candidates']
    code=str(data.get('regency_city_code') or '')
    selected=next((c for c in candidates if c['regency_city_code']==code),None)
    if decision=='CONFIRMED':
        if not selected or len(candidates)!=1:
            raise ValueError('Cannot confirm an ambiguous or unsupported Kabupaten/Kota')
        candidate_province=INDONESIAN_PROVINCE_ALIASES.get(
            selected['province_code'],[selected['province']])[0]
        if (province_status.get('incident_jurisdiction_verified') and
                province_status.get('incident_province')!=candidate_province):
            raise ValueError('Confirmed province disagrees with the selected Kabupaten/Kota')
    elif code and not selected:
        raise ValueError('Selected Kabupaten/Kota is not supported by source')
    payload={
        'campaign_id':campaign.id,'result_id':post.id,
        'decision':decision,
        'regency_city_code':selected['regency_city_code'] if selected else '',
        'regency_city':selected['regency_city'] if selected else '',
        'province':INDONESIAN_PROVINCE_ALIASES.get(
            selected['province_code'],[selected['province']])[0] if selected else '',
        'evidence_fingerprint':fingerprint(post.text_content),
        'assessment_version':latest.assessment_version,
        'rationale':rationale,
        'geographic_acl_expanded':False,
        'automatic_confirmation':False,
        'provider_called':False,
    }
    audit(db,p,'CampaignIncidentRegencyReview',
          f'{campaign.id}:{post.id}','INCIDENT_REGENCY_REVIEWED',payload)
    return regency_review_status(db,campaign.id,post.id,post)

def jurisdiction_action(db,p,action,data,id=None):
    if not has(p,'view_intelligence'):
        raise PermissionError('Intelligence access required')
    if action=='campaignJurisdictionReadiness':
        from .jurisdiction_readiness import campaign_jurisdiction_readiness
        return campaign_jurisdiction_readiness(
            db,p,id or data.get('campaign_id'),data.get('cursor'))
    campaign,post,relevant=scoped_post(
        db,p,id or data.get('campaign_id'),data.get('result_id'))
    if action=='campaignRegencyReviewHistory':
        return {**regency_review_history(db,campaign.id,post.id),
                'canonical_source_id':'social:'+str(post.id),
                'latest_review':regency_review_status(db,campaign.id,post.id,post),
                'paid_provider_called':False}
    locations=incident_location_cues(post.text_content)
    status=jurisdiction_status(db,campaign.id,post.id,post)
    city_preview=incident_regency_preview(post.text_content)
    related_preview=related_regency_mentions(db,p,campaign.id,post,city_preview['candidates'])
    assessment=(db.query(EvidenceAssessment).filter_by(
        campaign_id=campaign.id,result_id=post.id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).first())
    preview={'campaign_id':str(campaign.id),'result_id':str(post.id),
        'canonical_source_id':'social:'+str(post.id),
        'source_fingerprint':fingerprint(post.text_content),
        'current_assessment_version':assessment.assessment_version if assessment else 0,
        'source_context_provinces_unverified':locations,
        'incident_kabupaten_kota_preview':city_preview,
        'related_incident_place_mentions':related_preview,
        'source_post_relevance_assessed':relevant,
        'source_evidence_verified':False,
        'geographic_acl_expanded':False,
        'latest_review':status,
        'paid_provider_called':False}
    if action=='campaignJurisdictionPreview':return preview
    if action=='campaignRegencyReview':
        city_review=save_regency_review(db,p,campaign,post,relevant,data,status)
        return {**preview,'saved':True,'latest_review':jurisdiction_status(
            db,campaign.id,post.id,post),'regency_city_review':city_review}
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
    # Never allow a province decision to conflict with a current officer-
    # confirmed city; first reject that city decision through the audited flow.
    city_status=status.get('regency_city_review') or {}
    if city_status.get('incident_regency_city_verified'):
        if decision=='REJECTED' or province!=city_status.get('incident_province'):
            raise ValueError('Resolve confirmed Kabupaten/Kota before changing its province')
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
