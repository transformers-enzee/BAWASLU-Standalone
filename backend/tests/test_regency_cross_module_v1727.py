"""v172.7: chained locality extraction and cross-module officer statuses."""
from app.incident_regency_candidates import incident_regency_preview
from app.jurisdiction_review import jurisdiction_action,jurisdiction_status
from app.models import SocialListeningResult
from app.saved_assessment_views import saved_classifications_for_posts
from app.campaigns import campaign_action
from test_regency_officer_review_v1723 import fixture,ready,preview,submit,user

def test_third_and_fourth_explicit_places_are_not_dropped():
    text=('Dugaan pelanggaran terjadi di Kota Bandung dan Kota Cimahi '
          'serta Kabupaten Bandung dan Kabupaten Bogor.')
    result=incident_regency_preview(text)
    assert result['candidate_count']==4
    assert result['multiple_regency_candidates']
    assert not result['kabupaten_kota_verified']

def test_confirmed_city_visible_to_inbox_and_watchlist_saved_assessments():
    db=fixture()
    try:
        ready(db)
        submit(db,preview(db))
        source=db.get(SocialListeningResult,1)
        saved=saved_classifications_for_posts(db,user(),[source])[1]
        assert saved[0]['incident_jurisdiction_review']['regency_city_review'][
          'incident_regency_city_verified'] is True
        inbox=campaign_action(db,user(),'campaignIntelligenceInbox',{'campaign_id':'91'})
        assert inbox['findings'][0]['incident_jurisdiction_review'][
          'regency_city_review']['incident_regency_city']=='Kota Bandung'
        assert inbox['findings'][0]['incident_jurisdiction_verified'] is False
    finally:db.close()

def test_rejected_city_is_not_verified_across_modules():
    db=fixture()
    try:
        ready(db);submit(db,preview(db),'REJECTED')
        source=db.get(SocialListeningResult,1)
        saved=saved_classifications_for_posts(db,user(),[source])[1]
        assert saved[0]['incident_jurisdiction_review']['regency_city_review'][
          'decision']=='REJECTED'
        assert not saved[0]['incident_jurisdiction_review']['regency_city_review'][
          'incident_regency_city_verified']
    finally:db.close()
