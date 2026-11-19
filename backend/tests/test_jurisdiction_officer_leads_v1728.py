"""v172.8: bounded officer-review queue from real authorized evidence."""
from app.jurisdiction_readiness import campaign_jurisdiction_readiness
from app.jurisdiction_review import jurisdiction_action
from app.models import SocialListeningResult, CampaignEvidence, EvidenceAssessment
from test_regency_officer_review_v1723 import fixture,ready,preview,submit,user

def report(db):
    return jurisdiction_action(db,user(),'campaignJurisdictionReadiness',{},'91')

def test_review_leads_are_prioritized_and_only_human_confirmed():
    db=fixture()
    try:
        ready(db)
        db.add(SocialListeningResult(id=2,run_id=1,platform='Instagram',
          text_content='Kasus pemilu terjadi di Kota Bandung dan Kota Cimahi.',
          canonical_url='https://example.test/post/2'))
        db.add(CampaignEvidence(campaign_id=91,result_id=2))
        db.add(EvidenceAssessment(campaign_id=91,result_id=2,
            assessment_version=1,relevance_label='RELEVANT'))
        db.commit()
        data=report(db)
        assert data['counts']['relevant_sources']==2
        assert [x['priority'] for x in data['officer_review_leads']]==[
           'MULTIPLE_INCIDENT_LOCALITIES','EXPLICIT_LOCALITY_AWAITING_OFFICER']
        assert all(x['not_independently_verified'] and x['review_is_human_only']
                   for x in data['officer_review_leads'])
        assert data['review_leads_are_source_cues_not_approval']
        assert data['database_writes']==0
        assert data['no_provider_calls']
    finally: db.close()

def test_reviewed_city_removed_from_open_leads():
    db=fixture()
    try:
        ready(db)
        assert len(report(db)['officer_review_leads'])==1
        submit(db,preview(db))
        data=report(db)
        assert data['counts']['city_confirmed']==1
        assert data['officer_review_leads']==[]
    finally:db.close()

def test_unsafe_original_source_url_never_exposed():
    db=fixture()
    try:
        ready(db)
        db.get(SocialListeningResult,1).canonical_url='javascript:alert(1)'
        db.commit()
        lead=report(db)['officer_review_leads'][0]
        assert lead['original_source_url'] is None
        assert lead['canonical_source_id']=='social:1'
    finally:db.close()
