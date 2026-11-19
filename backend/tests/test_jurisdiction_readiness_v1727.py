"""v172.7: bounded, permission-scoped campaign jurisdiction readiness."""
import pytest
from app.models import CampaignEvidence,SocialListeningResult,EvidenceAssessment
from app.jurisdiction_readiness import campaign_jurisdiction_readiness,SCAN_LIMIT
from app.jurisdiction_review import jurisdiction_action
from test_regency_officer_review_v1723 import fixture,ready,preview,submit,user

def report(db,principal=None):
    return jurisdiction_action(db,principal or user(),
      'campaignJurisdictionReadiness',{},'91')

def test_officer_sample_is_read_only_and_tracks_real_city_decisions():
    db=fixture()
    try:
        ready(db)
        before=report(db)
        assert before['counts']['authorized_sources']==1
        assert before['counts']['relevant_sources']==1
        assert before['counts']['single_city_candidate']==1
        assert before['counts']['city_unreviewed']==1
        assert before['officer_decision_coverage_percent_sample']==0.0
        assert before['not_geolocation_accuracy'] and before['not_client_acceptance']
        assert before['database_writes']==0 and before['no_provider_calls']
        submit(db,preview(db))
        after=report(db)
        assert after['counts']['city_confirmed']==1
        assert after['officer_decision_coverage_percent_sample']==100.0
    finally:db.close()

def test_sample_flags_ambiguity_and_does_not_extrapolate_full_corpus():
    db=fixture()
    try:
        ready(db)
        text=('Dugaan pelanggaran terjadi di Kota Bandung dan Kota Cimahi.')
        db.get(SocialListeningResult,1).text_content=text
        db.commit()
        x=report(db)
        assert x['counts']['multiple_city_candidates']==1
        assert x['counts']['city_confirmed']==0
        assert x['not_full_corpus_coverage']
        assert x['scope']=='AUTHORIZED_LATEST_CAMPAIGN_EVIDENCE_ONLY'
    finally:db.close()

def test_scope_prevents_other_provinces_and_unpermitted_campaigns():
    db=fixture()
    try:
        ready(db)
        with pytest.raises(PermissionError):
            report(db,user('Provincial Analyst','Bali'))
        with pytest.raises(ValueError,match='valid campaign'):
            campaign_jurisdiction_readiness(db,user(),'not-an-id')
    finally:db.close()

def test_bounded_window_is_disclosed_and_not_estimated():
    db=fixture()
    try:
        ready(db)
        for ix in range(2,SCAN_LIMIT+3):
            db.add(SocialListeningResult(id=ix,run_id=1,platform='X',
                text_content='No explicit location in this unrelated source.'))
            db.add(CampaignEvidence(campaign_id=91,result_id=ix))
        db.commit()
        x=report(db)
        assert x['sampled_link_count']==SCAN_LIMIT
        assert x['more_evidence_may_exist']
        assert x['incomplete_for_campaign']
        assert x['counts']['relevant_sources']==0
        assert x['officer_decision_coverage_percent_sample'] is None
    finally:db.close()
