"""Permission-scoped, bounded and entirely read-only jurisdiction readiness.

Counts are for the newest saved campaign evidence links only. The result is
a triage sample, not complete field coverage, geolocation accuracy, or approval.
"""
from .access import allowed, has
from .models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
                     EvidenceAssessment)
from .socialcrawl import _result_in_scope
from .incident_regency_candidates import incident_regency_preview
from .jurisdiction_review import jurisdiction_status
from .related_incident_locations import _safe_source_url

SCAN_LIMIT=30

def campaign_jurisdiction_readiness(db, principal, campaign_id):
    if not has(principal,'view_intelligence'):
        raise PermissionError('Intelligence access required')
    if not str(campaign_id or '').isdigit() or int(campaign_id)<1:
        raise ValueError('Select a valid campaign')
    campaign=db.get(MonitoringCampaign,int(campaign_id))
    if not campaign or not allowed(principal,campaign):
        raise PermissionError('Campaign unavailable')
    links=(db.query(CampaignEvidence).filter_by(campaign_id=campaign.id)
           .order_by(CampaignEvidence.id.desc()).limit(SCAN_LIMIT+1).all())
    sampled_links=links[:SCAN_LIMIT]
    ids=[link.result_id for link in sampled_links]
    posts={post.id:post for post in (
        db.query(SocialListeningResult)
        .filter(SocialListeningResult.id.in_(ids)).all() if ids else [])}
    # Use the saved assessment with highest version, identical to Inbox logic.
    assessments={}
    if ids:
        rows=(db.query(EvidenceAssessment)
              .filter(EvidenceAssessment.campaign_id==campaign.id,
                      EvidenceAssessment.result_id.in_(ids))
              .order_by(EvidenceAssessment.assessment_version.desc(),
                        EvidenceAssessment.id.desc()).all())
        for row in rows:
            assessments.setdefault(row.result_id,row)
    keys=('authorized_sources','relevant_sources','unassessed_or_irrelevant',
          'no_explicit_city_candidate','single_city_candidate',
          'multiple_city_candidates','multi_province_candidates',
          'city_confirmed','city_rejected','city_unreviewed',
          'city_stale_or_conflicted','province_confirmed')
    counts={key:0 for key in keys}
    leads=[]
    for link in sampled_links:
        post=posts.get(link.result_id)
        if not post or not _result_in_scope(db,principal,post):
            continue
        counts['authorized_sources']+=1
        assessment=assessments.get(post.id)
        relevant=bool(assessment and str(assessment.relevance_label or '').upper()
                      in ('RELEVANT','HIGHLY_RELEVANT'))
        if not relevant:
            counts['unassessed_or_irrelevant']+=1
            continue
        counts['relevant_sources']+=1
        cues=incident_regency_preview(post.text_content)
        if cues['candidate_count']==0:counts['no_explicit_city_candidate']+=1
        elif cues['candidate_count']==1:counts['single_city_candidate']+=1
        else:counts['multiple_city_candidates']+=1
        if cues['multiple_provinces']:
            counts['multi_province_candidates']+=1
        review=jurisdiction_status(db,campaign.id,post.id,post)
        if review.get('incident_jurisdiction_verified'):
            counts['province_confirmed']+=1
        city=review.get('regency_city_review') or {}
        if city.get('incident_regency_city_verified'):
            counts['city_confirmed']+=1
        elif city.get('decision')=='REJECTED':
            counts['city_rejected']+=1
        elif str(city.get('decision') or '').startswith('STALE_') or (
            city.get('decision')=='PROVINCE_REVIEW_CONFLICT'):
            counts['city_stale_or_conflicted']+=1
        else:
            counts['city_unreviewed']+=1
        if not city.get('incident_regency_city_verified') and (
            len(leads)<SCAN_LIMIT):
            if city.get('decision')=='PROVINCE_REVIEW_CONFLICT' or (
                str(city.get('decision') or '').startswith('STALE_')):
                priority='STALE_OR_CONFLICTED'
            elif cues['multiple_regency_candidates']:
                priority='MULTIPLE_INCIDENT_LOCALITIES'
            elif cues['candidate_count']==1:
                priority='EXPLICIT_LOCALITY_AWAITING_OFFICER'
            else:
                priority='NO_EXPLICIT_CITY_CUE'
            leads.append({
                'result_id':str(post.id),
                'canonical_source_id':'social:'+str(post.id),
                'priority':priority,
                'current_city_decision':str(city.get('decision') or 'UNREVIEWED'),
                'candidate_regency_cities':[c['regency_city']
                                            for c in cues['candidates']],
                'original_source_url':_safe_source_url(post.canonical_url),
                'not_independently_verified':True,
                'review_is_human_only':True,
            })
    total=counts['relevant_sources']
    # Not a field accuracy or a system acceptance percentage.
    reviewed=counts['city_confirmed']+counts['city_rejected']
    ordering={
      'STALE_OR_CONFLICTED':0,
      'MULTIPLE_INCIDENT_LOCALITIES':1,
      'EXPLICIT_LOCALITY_AWAITING_OFFICER':2,
      'NO_EXPLICIT_CITY_CUE':3}
    leads.sort(key=lambda row:ordering.get(row['priority'],9))
    return {
      'campaign_id':str(campaign.id),
      'scope':'AUTHORIZED_LATEST_CAMPAIGN_EVIDENCE_ONLY',
      'scan_limit':SCAN_LIMIT,
      'sampled_link_count':len(sampled_links),
      'authorized_link_count':counts['authorized_sources'],
      'more_evidence_may_exist':len(links)>SCAN_LIMIT,
      'incomplete_for_campaign':len(links)>SCAN_LIMIT,
      'counts':counts,
      'officer_review_leads':leads[:12],
      'review_lead_limit':12,
      'review_leads_truncated':len(leads)>12,
      'review_leads_are_source_cues_not_approval':True,
      'officer_decision_coverage_percent_sample':(
          round(100*reviewed/total,1) if total else None),
      'not_full_corpus_coverage':True,
      'not_geolocation_accuracy':True,
      'not_client_acceptance':True,
      'no_provider_calls':True,
      'database_writes':0,
      'geographic_acl_expanded':False,
    }
