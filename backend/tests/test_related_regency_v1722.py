"""v172.2: source-linked cross-platform locality review with safe provenance."""
from datetime import datetime, timezone, timedelta
from app.related_incident_locations import (
    _published_utc, _safe_source_url, related_regency_mentions)
from app.models import SocialListeningResult, CampaignEvidence
from test_related_regency_v1721 import setup, auth
from app.incident_regency_candidates import incident_regency_candidates

def test_url_validation_rejects_non_https_and_credentials():
    assert _safe_source_url('https://example.test/post/2')=='https://example.test/post/2'
    for value in ('javascript:alert(1)','http://example.test/x',
                  'https://user:secret@example.test/x','https://example.test/a b',
                  '//example.test/x', 'https://'):
        assert _safe_source_url(value) is None

def test_publication_requires_time_zone():
    assert _published_utc('2026-11-18T12:00:00Z')==datetime(
        2026,11,18,12,tzinfo=timezone.utc)
    assert _published_utc('2026-11-18T12:00:00') is None
    assert _published_utc('not a date') is None

def test_related_mentions_show_platform_and_provenance_without_confirmation():
    db=setup()
    try:
        source=db.get(SocialListeningResult,1)
        source.published_at='2026-11-18T12:00:00Z'
        second=db.get(SocialListeningResult,2)
        second.published_at='2026-11-18T14:00:00Z'
        third=db.get(SocialListeningResult,3)
        third.published_at='2026-10-01T12:00:00Z'
        third.canonical_url='javascript:alert(1)'
        db.commit()
        data=related_regency_mentions(db,auth(),9,source,
                                      incident_regency_candidates(source.text_content))
        group=data['candidate_matches'][0]
        assert group['cross_platform_review_lead']
        assert group['distinct_platforms']==['Instagram','X']
        assert group['within_72_hours_count']==1
        by_id={x['result_id']:x for x in group['related_mentions']}
        assert by_id['2']['publication_window_status']=='WITHIN_72_HOURS'
        assert by_id['3']['publication_window_status']=='BEYOND_72_HOURS'
        assert by_id['2']['original_source_url']=='https://example.test/2'
        assert by_id['3']['original_source_url'] is None
        assert not data['same_incident_established']
        assert data['platform_variety_is_not_independent_corroboration']
        assert not by_id['2']['source_evidence_verified']
    finally:db.close()

def test_unknown_dates_do_not_support_temporal_correspondence():
    db=setup()
    try:
        source=db.get(SocialListeningResult,1)
        data=related_regency_mentions(db,auth(),9,source,
                                      incident_regency_candidates(source.text_content))
        assert data['candidate_matches'][0]['within_72_hours_count']==0
        assert all(x['publication_window_status']=='UNKNOWN_PUBLICATION_TIME'
                   for x in data['candidate_matches'][0]['related_mentions'])
    finally:db.close()
