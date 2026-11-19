"""Read-only same-campaign locality mention inventory for officer review.

A matched place name across posts is not proof that posts discuss the same
event. Records stay in the caller's existing campaign and geographic scope.
"""
from datetime import datetime, timezone
from urllib.parse import urlparse
from .models import CampaignEvidence, SocialListeningResult
from .socialcrawl import _result_in_scope
from .incident_regency_candidates import incident_regency_candidates
import hashlib
import re

def fingerprint(text):
    return hashlib.sha256(re.sub(r'\s+', ' ', str(text or '').casefold()).strip().encode()).hexdigest()

def _safe_source_url(value):
    """Allow external source navigation only for genuine HTTPS URLs."""
    raw=str(value or '').strip()
    try:
        parsed=urlparse(raw)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
            return None
        if any(c.isspace() for c in raw) or len(raw)>2048:
            return None
    except ValueError:
        return None
    return raw

def _published_utc(value):
    """Unknown and timezone-naive source dates are not comparable."""
    raw=str(value or '').strip()
    if not raw:
        return None
    try:
        date=datetime.fromisoformat(raw.replace('Z','+00:00'))
        return date.astimezone(timezone.utc) if date.tzinfo else None
    except (ValueError, OverflowError):
        return None

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
    source_date=_published_utc(source_post.published_at)
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
            publication=_published_utc(post.published_at)
            gap_hours=(abs((publication-source_date).total_seconds())/3600
                       if publication and source_date else None)
            matches[code].append({
                'result_id':str(post.id),
                'platform':str(post.platform or 'Unknown'),
                'canonical_source_id':'social:'+str(post.id),
                'original_source_url':_safe_source_url(post.canonical_url),
                'publication_window_status':(
                    'WITHIN_72_HOURS' if gap_hours is not None and gap_hours<=72 else
                    'BEYOND_72_HOURS' if gap_hours is not None else
                    'UNKNOWN_PUBLICATION_TIME'),
                'source_evidence_verified':False,
                'same_incident_verified':False,
            })
    return {'candidate_matches':[
        {'regency_city_code':candidate['regency_city_code'],
         'regency_city':candidate['regency_city'],
         'related_mentions':matches[candidate['regency_city_code']],
         'related_mention_count':len(matches[candidate['regency_city_code']]),
         'distinct_platforms':sorted({
             item['platform'] for item in matches[candidate['regency_city_code']]}),
         'cross_platform_review_lead':len({
             item['platform'] for item in matches[candidate['regency_city_code']]
         } | {str(source_post.platform or 'Unknown')})>1,
         'within_72_hours_count':sum(
             item['publication_window_status']=='WITHIN_72_HOURS'
             for item in matches[candidate['regency_city_code']]),
         'temporal_overlap_is_not_same_incident_proof':True}
        for candidate in candidates],
        'scan_cap':max_scanned,'truncated_possible':truncated,
        'independent_incident_verified':False,'same_incident_established':False,
        'matching_place_is_not_same_incident_proof':True,
        'platform_variety_is_not_independent_corroboration':True,
        'publication_windows_are_review_cues_only':True,
        'paid_provider_called':False}
