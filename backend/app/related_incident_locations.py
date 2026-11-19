"""Read-only same-campaign locality mention inventory for officer review.

A matched place name across posts is not proof that posts discuss the same
event. Records stay in the caller's existing campaign and geographic scope.
"""
from sqlalchemy import select
from .models import CampaignEvidence, SocialListeningResult
from .socialcrawl import _result_in_scope
from .incident_regency_candidates import incident_regency_candidates
import hashlib
import re

def fingerprint(text):
    return hashlib.sha256(re.sub(r'\s+', ' ', str(text or '').casefold()).strip().encode()).hexdigest()

def related_regency_mentions(db, principal, campaign_id, source_post, candidates, *,
                              max_scanned=200, max_per_candidate=5):
    if not candidates:
        return {'candidate_matches':[], 'scan_cap':max_scanned,
                'truncated_possible':False, 'independent_incident_verified':False,
                'same_incident_established':False, 'paid_provider_called':False}
    wanted={x['regency_city_code'] for x in candidates}
    matches={code:[] for code in wanted}
    seen={code:set() for code in wanted}
    source_fingerprint=fingerprint(source_post.text_content)
    # The campaign and source themselves were independently permission-checked
    # by scoped_post. Enforce result-level scope again for every related source.
    rows=(db.query(SocialListeningResult)
          .join(CampaignEvidence,CampaignEvidence.result_id==SocialListeningResult.id)
          .filter(CampaignEvidence.campaign_id==int(campaign_id),
                  SocialListeningResult.id!=source_post.id)
          .order_by(CampaignEvidence.id.desc())
          .limit(max_scanned+1).all())
    truncated=len(rows)>max_scanned
    for post in rows[:max_scanned]:
        if not _result_in_scope(db,principal,post):
            continue
        if fingerprint(post.text_content)==source_fingerprint:
            continue
        place_codes={x['regency_city_code'] for x in
                     incident_regency_candidates(post.text_content)}
        for code in sorted(wanted.intersection(place_codes)):
            if len(matches[code])>=max_per_candidate:
                continue
            # Avoid repeated source URLs for identical provider posts.
            url=str(post.canonical_url or '').strip().casefold()
            dedup=url or f'result:{post.id}'
            if dedup in seen[code]: continue
            seen[code].add(dedup)
            matches[code].append({'result_id':str(post.id),
                                  'platform':str(post.platform or 'Unknown'),
                                  'canonical_source_id':'social:'+str(post.id)})
    return {'candidate_matches':[
        {'regency_city_code':candidate['regency_city_code'],
         'regency_city':candidate['regency_city'],
         'related_mentions':matches[candidate['regency_city_code']],
         'related_mention_count':len(matches[candidate['regency_city_code']])}
        for candidate in candidates],
        'scan_cap':max_scanned,'truncated_possible':truncated,
        'independent_incident_verified':False,'same_incident_established':False,
        'matching_place_is_not_same_incident_proof':True,
        'paid_provider_called':False}
