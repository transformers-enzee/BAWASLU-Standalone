"""v172.4: officer evidence revision, province/city agreement and audit history."""
import pytest
from app.jurisdiction_review import jurisdiction_action,jurisdiction_status
from app.models import SocialListeningResult,EvidenceAssessment,AuditEvent
from test_regency_officer_review_v1723 import ready,preview,submit,user,fixture
from app.geography import province_code_for

def test_review_history_keeps_old_decisions_and_scope():
    db=fixture()
    try:
        ready(db);submit(db,preview(db))
        submit(db,preview(db),'REJECTED')
        history=jurisdiction_action(db,user(),'campaignRegencyReviewHistory',
            {'result_id':'1'},'91')
        assert history['read_only'] and history['audit_events_are_not_current_verification']
        assert [x['decision'] for x in history['history']]==['REJECTED','CONFIRMED']
        assert not history['history'][1]['historical_decision_not_current_verification'] is False
        assert history['paid_provider_called'] is False
        with pytest.raises(PermissionError):
            jurisdiction_action(db,user('Provincial Analyst','Bali'),
                'campaignRegencyReviewHistory',{'result_id':'1'},'91')
    finally:db.close()

def test_stale_assessment_expected_version_cannot_commit_review():
    db=fixture()
    try:
        ready(db);p=preview(db)
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=2,
            relevance_label='RELEVANT',sentiment='NEUTRAL'))
        db.commit()
        with pytest.raises(ValueError,match='Saved assessment changed'):
            submit(db,p)
        assert db.query(AuditEvent).filter_by(
            subject_type='CampaignIncidentRegencyReview').count()==0
    finally:db.close()

def test_city_confirmation_cannot_be_overridden_by_rejecting_province():
    db=fixture()
    try:
        ready(db);submit(db,preview(db))
        with pytest.raises(ValueError,match='Resolve confirmed Kabupaten'):
            jurisdiction_action(db,user(),'campaignJurisdictionReview',{
                'result_id':'1','decision':'REJECTED',
                'rationale':'Rejecting this source without reviewing the verified city.'},'91')
        assert jurisdiction_status(db,91,1,db.get(SocialListeningResult,1))[
            'regency_city_review']['incident_regency_city_verified']
    finally:db.close()

def test_conflicting_preexisting_province_downgrades_city_verification():
    db=fixture()
    try:
        ready(db);submit(db,preview(db))
        from app.models import CampaignJurisdictionReview
        from app.jurisdiction_review import fingerprint
        db.add(CampaignJurisdictionReview(campaign_id=91,result_id=1,
            province='Bali',evidence_fingerprint=fingerprint(
                db.get(SocialListeningResult,1).text_content),
            decision='CONFIRMED',rationale='Old incompatible province decision.'))
        db.commit()
        status=jurisdiction_status(db,91,1,db.get(SocialListeningResult,1))
        assert status['regency_city_review']['decision']=='PROVINCE_REVIEW_CONFLICT'
        assert not status['regency_city_review']['incident_regency_city_verified']
    finally:db.close()

def test_history_is_bounded_and_never_marks_old_review_as_current():
    db=fixture()
    try:
        ready(db)
        for _ in range(14):
            submit(db,preview(db),'REJECTED')
        h=jurisdiction_action(db,user(),'campaignRegencyReviewHistory',
            {'result_id':'1'},'91')
        assert len(h['history'])==12
        assert h['history_may_be_truncated']
        assert all(x['historical_decision_not_current_verification'] for x in h['history'])
    finally:db.close()
