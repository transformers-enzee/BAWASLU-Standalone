"""v172.9: bounded officer readiness keyset and off-window evidence lookup."""
import pytest
from app.models import (CampaignEvidence,SocialListeningResult,
                        EvidenceAssessment)
from app.jurisdiction_readiness import campaign_jurisdiction_readiness,SCAN_LIMIT
from app.jurisdiction_review import jurisdiction_action
from app.campaigns import campaign_action
from test_regency_officer_review_v1723 import fixture,ready,user

def readiness(db,cursor=None,principal=None):
    return jurisdiction_action(db,principal or user(),
       'campaignJurisdictionReadiness',
       {'cursor':cursor} if cursor is not None else {},'91')

def populate(db,number=SCAN_LIMIT+4):
    ready(db)
    for i in range(2,number+1):
        db.add(SocialListeningResult(id=i,run_id=1,platform='X',
            text_content='Dugaan kasus terjadi di Kota Bandung.',
            canonical_url='https://example.test/post/'+str(i)))
        db.add(CampaignEvidence(campaign_id=91,result_id=i))
        db.add(EvidenceAssessment(campaign_id=91,result_id=i,
            assessment_version=1,relevance_label='RELEVANT'))
    db.commit()

def test_keyset_pages_are_distinct_and_oldest_review_is_reachable():
    db=fixture()
    try:
        populate(db)
        first=readiness(db)
        second=readiness(db,first['next_cursor'])
        a={lead['result_id'] for lead in first['officer_review_leads']}
        b={lead['result_id'] for lead in second['officer_review_leads']}
        assert first['sampled_link_count']==SCAN_LIMIT
        assert first['next_cursor']
        assert second['page_cursor']==first['next_cursor']
        assert second['next_cursor'] is None
        assert first['pagination_method']=='DESCENDING_EVIDENCE_ID_KEYSET'
        assert not (a & b)
        assert first['not_full_corpus_coverage'] and second['not_geolocation_accuracy']
        assert '1' in b
    finally: db.close()

@pytest.mark.parametrize('cursor',[-1,'foo',0,{},'NaN'])
def test_invalid_readiness_cursors_fail_closed(cursor):
    db=fixture()
    try:
        with pytest.raises(ValueError,match='cursor'):
            readiness(db,cursor)
    finally: db.close()

def test_review_window_keeps_campaign_scope_and_avoids_watchlist_only_links():
    db=fixture()
    try:
        ready(db)
        db.add(SocialListeningResult(id=2,run_id=1,platform='X',
            text_content='Kasus terjadi di Kota Bandung.'))
        db.add(CampaignEvidence(campaign_id=91,result_id=2,match_method='WATCHLIST_ACCOUNT'))
        db.add(EvidenceAssessment(campaign_id=91,result_id=2,
             assessment_version=1,relevance_label='RELEVANT'))
        db.commit()
        r=readiness(db)
        assert r['sampled_link_count']==1
        assert r['counts']['authorized_sources']==1
        with pytest.raises(PermissionError):
            readiness(db,principal=user('Provincial Analyst','Bali'))
    finally: db.close()

def test_exact_scoped_post_lookup_works_when_outside_loaded_inbox_page():
    db=fixture()
    try:
        populate(db)
        response=campaign_action(db,user(),'campaignIntelligenceInbox',{
            'campaign_id':'91','result_id':'1',
            'paged':True,'page_size':1})
        records=response['findings']
        assert records
        assert records[0]['id']=='1' or str(records[0]['id'])=='1'
        assert str(records[0]['campaign_id'])=='91'
        assert response['paid_provider_called'] is False
        assert records[0]['incident_jurisdiction_review']['regency_city_review'][
            'incident_regency_city_verified'] is False
    finally:db.close()

def test_exact_post_lookup_cannot_cross_campaign_or_region():
    db=fixture()
    try:
        populate(db)
        response=campaign_action(db,user(),'campaignIntelligenceInbox',{
            'campaign_id':'999','result_id':'1','paged':True,'page_size':1})
        assert response['findings']==[]
        with pytest.raises(PermissionError):
            readiness(db,principal=user('Provincial Analyst','Bali'))
    finally:db.close()
