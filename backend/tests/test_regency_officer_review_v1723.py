"""v172.3: append-only officer Kabupaten/Kota review remains source-bound."""
import pytest
from app.models import SocialListeningResult,EvidenceAssessment,AuditEvent
from app.jurisdiction_review import jurisdiction_action,jurisdiction_status
from test_jurisdiction_cross_module import fixture,user

TEXT='Dugaan pelanggaran pemilu terjadi di Kota Bandung.'

def ready(db):
    post=db.get(SocialListeningResult,1)
    post.text_content=TEXT
    db.commit()
    return post

def preview(db):
    return jurisdiction_action(db,user(),'campaignJurisdictionPreview',
        {'result_id':'1'},'91')

def submit(db,pre,decision='CONFIRMED',code=None):
    candidates=pre['incident_kabupaten_kota_preview']['candidates']
    if code is None:code=candidates[0]['regency_city_code'] if candidates else ''
    return jurisdiction_action(db,user(),'campaignRegencyReview',{
        'result_id':'1','decision':decision,'regency_city_code':code,
        'rationale':'The original source explicitly states the incident happened here.',
        'expected_source_fingerprint':pre['source_fingerprint'],
        'expected_review_event_id':pre['latest_review']['regency_city_review']['review_event_id'],
    },'91')

def test_officer_verifies_city_with_append_only_audit_no_acl_changes():
    db=fixture()
    try:
        ready(db);p=preview(db);result=submit(db,p)
        city=result['latest_review']['regency_city_review']
        assert city['decision']=='CONFIRMED'
        assert city['incident_regency_city']=='Kota Bandung'
        assert city['incident_regency_city_verified']
        assert result['latest_review']['incident_jurisdiction_verified'] is False
        assert not result['geographic_acl_expanded']
        assert db.query(AuditEvent).filter_by(
            subject_type='CampaignIncidentRegencyReview').count()==1
        latest=jurisdiction_status(db,91,1,db.get(SocialListeningResult,1))
        assert latest['regency_city_review']['incident_regency_city_verified']
        assert result['paid_provider_called'] is False
    finally:db.close()

def test_city_review_is_rejected_when_source_changed_after_preview():
    db=fixture()
    try:
        ready(db);p=preview(db)
        db.get(SocialListeningResult,1).text_content='Dugaan pelanggaran di Bali.'
        db.commit()
        with pytest.raises(ValueError,match='Source changed'):
            submit(db,p)
        assert db.query(AuditEvent).filter_by(
            subject_type='CampaignIncidentRegencyReview').count()==0
    finally:db.close()

def test_only_source_supported_unambiguous_city_is_confirmable():
    db=fixture()
    try:
        ready(db);p=preview(db)
        with pytest.raises(ValueError,match='ambiguous or unsupported'):
            submit(db,p,code='99.99')
        db.get(SocialListeningResult,1).text_content=(
            'Dugaan pelanggaran pemilu terjadi di Kota Bandung dan Kota Cimahi.')
        db.commit()
        p=preview(db)
        with pytest.raises(ValueError,match='ambiguous or unsupported'):
            submit(db,p)
    finally:db.close()

def test_revoked_permission_and_nonrelevant_assessment_cannot_verify():
    db=fixture()
    try:
        ready(db);p=preview(db)
        payload={'result_id':'1','decision':'CONFIRMED',
            'regency_city_code':p['incident_kabupaten_kota_preview']['candidates'][0]['regency_city_code'],
            'rationale':'The original incident statement mentions Kota Bandung.',
            'expected_source_fingerprint':p['source_fingerprint'],
            'expected_review_event_id':0}
        with pytest.raises(PermissionError):
            jurisdiction_action(db,user('Provincial Analyst'),
                'campaignRegencyReview',payload,'91')
        db.query(EvidenceAssessment).one().relevance_label='UNASSESSED'
        db.commit()
        with pytest.raises(ValueError,match='Relevant saved assessment'):
            jurisdiction_action(db,user(),'campaignRegencyReview',payload,'91')
    finally:db.close()

def test_separate_officer_revision_and_rejection_keep_history():
    db=fixture()
    try:
        ready(db);p=preview(db);saved=submit(db,p)
        p=preview(db);rejected=submit(db,p,'REJECTED')
        assert rejected['latest_review']['regency_city_review']['decision']=='REJECTED'
        assert not rejected['latest_review']['regency_city_review']['incident_regency_city_verified']
        assert db.query(AuditEvent).filter_by(
            subject_type='CampaignIncidentRegencyReview').count()==2
        with pytest.raises(ValueError,match='Review changed'):
            submit(db,p,'CONFIRMED')
    finally:db.close()

def test_city_review_becomes_stale_when_assessment_version_changes():
    db=fixture()
    try:
        ready(db);p=preview(db);submit(db,p)
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=2,
            relevance_label='RELEVANT',sentiment='NEUTRAL'))
        db.commit()
        r=jurisdiction_status(db,91,1,db.get(SocialListeningResult,1))
        assert r['regency_city_review']['decision']=='STALE_ASSESSMENT_CHANGED'
        assert not r['regency_city_review']['incident_regency_city_verified']
    finally:db.close()
