"""v172.1: bounded campaign-local locality cross-post review cues."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.jurisdiction_review import jurisdiction_action
from app.access import default_permissions

def auth():
    role='National Administrator'
    return {'id':'11','role':role,'geographic_scope':'Nationwide',
        'status':'Active','permissions':default_permissions(role)}

def setup():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    db.add_all([
        MonitoringCampaign(id=9,name='local',province='Jawa Barat',created_by='11',
            primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'),
        MonitoringCampaign(id=10,name='other',province='Jawa Barat',created_by='11',
            primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'),
    ])
    texts={
        1:'Dugaan pelanggaran pemilu terjadi di Kota Bandung.',
        2:'Laporan pemilu terjadi di Kota Bandung kemarin.',
        3:'Laporan pemilu terjadi di Kota Bandung kemarin.',
        4:'Kasus pemilu terjadi di Kota Surabaya.',
        5:'Insiden pemilu terjadi di Kota Bandung.',
        6:'Akun dari Kota Bandung membahas pemilu.',
    }
    for id,text in texts.items():
        db.add(SocialListeningResult(id=id,run_id=1,text_content=text,
            platform='Instagram' if id==2 else 'X',
            canonical_url='https://example.test/'+str(id)))
        db.add(CampaignEvidence(campaign_id=10 if id==5 else 9,result_id=id))
    db.add(EvidenceAssessment(campaign_id=9,result_id=1,
        assessment_version=1,relevance_label='RELEVANT',sentiment='NEUTRAL'))
    db.commit()
    return db

def test_related_localities_are_campaign_scoped_without_duplicates_or_guessing():
    db=setup()
    try:
        p=jurisdiction_action(db,auth(),'campaignJurisdictionPreview',
            {'result_id':'1'},'9')
        related=p['related_incident_place_mentions']
        matches=related['candidate_matches'][0]['related_mentions']
        assert [x['result_id'] for x in matches]==['3','2']
        assert all(x['canonical_source_id'].startswith('social:') for x in matches)
        assert not related['same_incident_established']
        assert not related['independent_incident_verified']
        assert related['paid_provider_called'] is False
        assert not p['geographic_acl_expanded']
    finally:db.close()

def test_no_candidate_does_not_scan_or_prove_location():
    db=setup()
    try:
        p=jurisdiction_action(db,auth(),'campaignJurisdictionPreview',
            {'result_id':'6'},'9')
        assert p['related_incident_place_mentions']['candidate_matches']==[]
        assert not p['related_incident_place_mentions']['same_incident_established']
    finally:db.close()

def test_cross_campaign_source_never_appears():
    db=setup()
    try:
        p=jurisdiction_action(db,auth(),'campaignJurisdictionPreview',
            {'result_id':'1'},'9')
        ids=[m['result_id'] for c in p['related_incident_place_mentions']['candidate_matches']
             for m in c['related_mentions']]
        assert '5' not in ids
        assert '4' not in ids
        assert '6' not in ids
    finally:db.close()
