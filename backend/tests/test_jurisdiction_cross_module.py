"""Human-reviewed jurisdiction and safe cross-module source assessment lookup.

No paid AI, no crawl, no inferred profile-based incident location.
"""
import json
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (User,AccessGrant,MonitoringCampaign,
    SocialListeningResult,CampaignEvidence,EvidenceAssessment,CampaignJurisdictionReview)
from app.access import default_permissions
from app.campaigns import campaign_action
from app.jurisdiction_review import jurisdiction_action, jurisdiction_status
from app.saved_assessment_views import saved_classifications_for_posts
from app.source_lineage import resolve_saved_assessments


TEXT='Dugaan pelanggaran di Riau terkait daftar pemilih dilaporkan warga.'

def user(role='National Administrator',province=''):
    if role=='National Administrator':
        return {'id':'11','role':role,'geographic_scope':'Nationwide',
            'status':'Active','permissions':default_permissions(role)}
    return {'id':'11','role':role,'geographic_scope':'Province',
        'province':province or 'Riau','status':'Active',
        'permissions':default_permissions(role)}


def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    db.add(MonitoringCampaign(id=91,name='Oversight in Riau',province='Riau',
        created_by='11',primary_keywords_json='["pemilu"]',
        secondary_keywords_json='[]',excluded_keywords_json='[]'))
    db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
        author_name='Reporter',text_content=TEXT,
        canonical_url='https://example.test/1',
        published_at='2026-10-29T00:00:00Z'))
    db.add(CampaignEvidence(campaign_id=91,result_id=1))
    db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
        relevance_label='RELEVANT',sentiment='NEUTRAL',sentiment_model='mock',
        potential_issue_signals_json='[]'))
    db.commit()
    return db


def test_incident_location_preview_is_readonly_and_uses_source_context():
    db=fixture()
    try:
        res=jurisdiction_action(db,user(),'campaignJurisdictionPreview',
            {'result_id':'1'},'91')
        assert res['source_context_provinces_unverified']==['Riau']
        assert res['latest_review']['decision']=='UNREVIEWED'
        assert db.query(CampaignJurisdictionReview).count()==0
        assert res['geographic_acl_expanded'] is False
        assert res['paid_provider_called'] is False
    finally:db.close()


def test_officer_can_verify_source_context_and_share_result_with_watchlist_and_inbox():
    db=fixture()
    try:
        saved=campaign_action(db,user(),'campaignJurisdictionReview',
            {'result_id':'1','decision':'CONFIRMED','province':'Riau',
             'rationale':'The source explicitly states suspected misconduct occurred in Riau.'},'91')
        assert saved['saved']
        assert saved['latest_review']['incident_jurisdiction_verified'] is True
        inbox=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91'})
        item=inbox['findings'][0]
        assert item['incident_jurisdiction_verified'] is True
        assert item['incident_jurisdiction_review']['incident_province']=='Riau'
        assert item['campaign_id']=='91'
        watchlist=saved_classifications_for_posts(
            db,user(),[db.get(SocialListeningResult,1)])[1][0]
        assert watchlist['incident_jurisdiction_review']['incident_province']=='Riau'
    finally:db.close()


def test_unsupported_or_ambiguous_provinces_must_not_be_verified():
    db=fixture()
    try:
        with pytest.raises(ValueError,match='ambiguous or unsupported'):
            jurisdiction_action(db,user(),'campaignJurisdictionReview',
              {'result_id':'1','decision':'CONFIRMED','province':'Bali',
               'rationale':'Wrong province despite a source saying Riau.'},'91')
        post=db.get(SocialListeningResult,1)
        post.text_content+=' Insiden di Bali juga dilaporkan.'
        db.commit()
        with pytest.raises(ValueError,match='ambiguous or unsupported'):
            jurisdiction_action(db,user(),'campaignJurisdictionReview',
              {'result_id':'1','decision':'CONFIRMED','province':'Riau',
               'rationale':'Two provinces are stated as possible incidents.'},'91')
        assert db.query(CampaignJurisdictionReview).count()==0
    finally:db.close()


def test_profile_location_is_not_incident_location_evidence():
    db=fixture()
    try:
        db.get(SocialListeningResult,1).text_content='Akun dari Riau membahas pemilu.'
        db.commit()
        result=jurisdiction_action(db,user(),'campaignJurisdictionPreview',
            {'result_id':'1'},'91')
        assert result['source_context_provinces_unverified']==[]
        with pytest.raises(ValueError,match='ambiguous or unsupported'):
            jurisdiction_action(db,user(),'campaignJurisdictionReview',
              {'result_id':'1','decision':'CONFIRMED','province':'Riau',
               'rationale':'Profile location does not prove the incident.'},'91')
    finally:db.close()


def test_source_edits_invalidate_previous_location_verification():
    db=fixture()
    try:
        jurisdiction_action(db,user(),'campaignJurisdictionReview',
            {'result_id':'1','decision':'CONFIRMED','province':'Riau',
             'rationale':'The quoted incident context names Riau.'},'91')
        post=db.get(SocialListeningResult,1)
        post.text_content='Dugaan pelanggaran di Bali sedang diperiksa.'
        db.commit()
        state=jurisdiction_status(db,91,1,post)
        assert state['decision']=='STALE_SOURCE_CHANGED'
        assert state['incident_jurisdiction_verified'] is False
    finally:db.close()


def test_officer_permissions_and_geographic_scope_enforced():
    db=fixture()
    try:
        with pytest.raises(PermissionError):
            jurisdiction_action(db,user('Provincial Analyst'),'campaignJurisdictionReview',
              {'result_id':'1','decision':'CONFIRMED','province':'Riau',
               'rationale':'This event is explicitly in Riau.'},'91')
        with pytest.raises(PermissionError):
            jurisdiction_action(db,user('Provincial Analyst','Bali'),
                'campaignJurisdictionPreview',{'result_id':'1'},'91')
        assert db.query(CampaignJurisdictionReview).count()==0
    finally:db.close()


def test_relevance_required_before_human_location_verification():
    db=fixture()
    try:
        db.query(EvidenceAssessment).one().relevance_label='UNASSESSED'
        db.commit()
        with pytest.raises(ValueError,match='Relevant saved assessment'):
            jurisdiction_action(db,user(),'campaignJurisdictionReview',
              {'result_id':'1','decision':'CONFIRMED','province':'Riau',
               'rationale':'Source has a quoted incident location.'},'91')
    finally:db.close()


def test_rejected_location_never_becomes_verified_location():
    db=fixture()
    try:
        result=jurisdiction_action(db,user(),'campaignJurisdictionReview',
            {'result_id':'1','decision':'REJECTED','province':'Riau',
             'rationale':'The named province is not confirmed as the incident location.'},'91')
        assert result['latest_review']['decision']=='REJECTED'
        assert result['latest_review']['incident_jurisdiction_verified'] is False
        assert result['latest_review']['incident_province'] is None
    finally:db.close()


def test_canonical_source_lookup_reuses_actual_saved_assessment_no_radar_id_collision():
    db=fixture()
    try:
        user_record=User(id=11,email='admin@example.test',
            full_name='Test Admin',password_hash='unused')
        db.add(user_record)
        db.add(AccessGrant(user_id=11,access_role='National Administrator',
            geographic_scope='Nationwide',status='Active',
            permissions_json=json.dumps(default_permissions('National Administrator'))))
        db.commit()
        result=resolve_saved_assessments('social:1',user=user_record,db=db)
        assert result['canonical_source_id']=='social:1'
        assert result['assessment_count']==1
        assert result['saved_assessments'][0]['sentiment']=='NEUTRAL'
        assert result['paid_provider_called'] is False
        with pytest.raises(HTTPException) as error:
            resolve_saved_assessments('radar:1',user=user_record,db=db)
        assert error.value.status_code==409
    finally:db.close()


def test_ui_jurisdiction_review_and_dispatch_are_explicit_and_free():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text(encoding='utf-8')
    assert 'Preview source-grounded location (free)' in source
    assert 'campaignJurisdictionReview' in source
    assert 'This does not change regional access permissions' in source
    assert 'Profile location does not establish incident jurisdiction' in source



def test_south_sumatra_repeat_voting_regency_context_is_one_unverified_province():
    """Real TikTok post 177: both named incident regencies are in one province."""
    db=fixture()
    try:
        post=db.get(SocialListeningResult,1)
        post.text_content=(
            'Badan Pengawas Pemilihan Umum atau Bawaslu Sumatra Selatan menemukan '
            'dugaan kasus warga mencoblos lebih dari sekali di Kabupaten '
            'Musi Banyuasin dan Musi Rawas Utara. #LintasiNews #Bawaslu'
        )
        db.commit()
        preview=jurisdiction_action(db,user(),'campaignJurisdictionPreview',
            {'result_id':'1'},'91')
        assert preview['source_context_provinces_unverified']==['Sumatera Selatan']
        assert preview['source_evidence_verified'] is False
        assert preview['latest_review']['decision']=='UNREVIEWED'
        assert preview['geographic_acl_expanded'] is False
        assert db.query(CampaignJurisdictionReview).count()==0
        confirmed=jurisdiction_action(db,user(),'campaignJurisdictionReview',
            {'result_id':'1','decision':'CONFIRMED','province':'Sumatera Selatan',
             'rationale':'The reported repeat voting is placed in Musi Banyuasin and Musi Rawas Utara.'},'91')
        assert confirmed['latest_review']['incident_jurisdiction_verified'] is True
        assert confirmed['latest_review']['incident_province']=='Sumatera Selatan'
        assert confirmed['geographic_acl_expanded'] is False
        assert confirmed['paid_provider_called'] is False
        assert db.get(MonitoringCampaign,91).province=='Riau'
    finally:db.close()


def test_south_sumatra_publisher_location_alone_is_not_incident_jurisdiction():
    db=fixture()
    try:
        post=db.get(SocialListeningResult,1)
        post.text_content=(
            'Bawaslu Sumatra Selatan berbicara tentang pemilu. '
            'Akun kantor berasal dari Kabupaten Musi Banyuasin.'
        )
        db.commit()
        preview=jurisdiction_action(db,user(),'campaignJurisdictionPreview',
            {'result_id':'1'},'91')
        assert preview['source_context_provinces_unverified']==[]
        with pytest.raises(ValueError,match='ambiguous or unsupported'):
            jurisdiction_action(db,user(),'campaignJurisdictionReview',
                {'result_id':'1','decision':'CONFIRMED','province':'Sumatera Selatan',
                 'rationale':'Publisher region is not proof of the incident location.'},'91')
        assert db.query(CampaignJurisdictionReview).count()==0
    finally:db.close()



def test_inbox_province_filter_reads_old_south_sumatra_source_not_only_current_page():
    """Province is a source mention filter, not verified incident jurisdiction."""
    db=fixture()
    try:
        # Place the incident story before 110 more-recent campaign links.
        db.add(SocialListeningResult(id=2,run_id=1,platform='tiktok',
            author_name='OfficialiNews',
            text_content=('Bawaslu Sumatra Selatan menemukan dugaan kasus warga '
                          'mencoblos lebih dari sekali di Kabupaten Musi Banyuasin '
                          'dan Musi Rawas Utara.'),
            canonical_url='https://example.test/south-sumatra',
            published_at='2024-02-18T13:00:00Z'))
        db.add(CampaignEvidence(campaign_id=91,result_id=2))
        db.add(EvidenceAssessment(campaign_id=91,result_id=2,assessment_version=1,
            relevance_label='RELEVANT',sentiment='NEUTRAL',
            potential_issue_signals_json='[]',geographic_signals_json='[]'))
        for n in range(3,114):
            db.add(SocialListeningResult(id=n,run_id=1,platform='instagram',
                author_name='Local account',text_content=f'Pemilu di Riau source {n}',
                canonical_url=f'https://example.test/{n}',
                published_at='2026-11-11T00:00:00Z'))
            db.add(CampaignEvidence(campaign_id=91,result_id=n))
            db.add(EvidenceAssessment(campaign_id=91,result_id=n,assessment_version=1,
                relevance_label='RELEVANT',sentiment='NEUTRAL',
                potential_issue_signals_json='[]'))
        db.commit()
        normal=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91','paged':True,'page_size':100})
        assert '2' not in {item['id'] for item in normal['findings']}
        filtered=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91','paged':True,'page_size':100,
             'province_filter':'Sumatera Selatan','include_totals':True})
        assert [item['id'] for item in filtered['findings']]==['2']
        assert filtered['findings'][0]['processing_hints']['province_mentions']==['Sumatera Selatan']
        assert filtered['full_statistics']['posts']==1
        assert filtered['findings'][0]['incident_jurisdiction_verified'] is False
        assert filtered['pagination']['has_more'] is False
    finally:db.close()


def test_source_province_filter_rejects_malformed_value():
    db=fixture()
    try:
        with pytest.raises(ValueError,match='Invalid province filter'):
            campaign_action(db,user(),'campaignIntelligenceInbox',
                {'campaign_id':'91','paged':True,'province_filter':'Riau% OR 1=1'})
    finally:db.close()


def test_province_dropdown_only_includes_authorized_eligible_inbox_posts():
    db=fixture()
    try:
        # One saved Riau assessment and one older South Sumatra source.
        db.add(SocialListeningResult(id=2,run_id=1,platform='tiktok',
            author_name='OfficialiNews',
            text_content=('Bawaslu Sumatra Selatan menemukan dugaan kasus warga '
                          'mencoblos lebih dari sekali di Kabupaten Musi Banyuasin '
                          'dan Musi Rawas Utara.'),
            canonical_url='https://example.test/177',
            published_at='2024-02-18T13:00:00Z'))
        db.add(CampaignEvidence(campaign_id=91,result_id=2))
        db.add(EvidenceAssessment(campaign_id=91,result_id=2,assessment_version=1,
            relevance_label='RELEVANT',sentiment='NEUTRAL',geographic_signals_json='[]'))
        # A different campaign must not contaminate a selected campaign's menu.
        db.add(MonitoringCampaign(id=92,name='East Java only',province='Jawa Timur',
            created_by='11',primary_keywords_json='["pemilu"]',
            secondary_keywords_json='[]',excluded_keywords_json='[]'))
        db.add(SocialListeningResult(id=3,run_id=1,platform='instagram',
            author_name='Reporter',text_content='Pelanggaran pemilu terjadi di Jawa Timur.',
            canonical_url='https://example.test/3',
            published_at='2026-11-10T00:00:00Z'))
        db.add(CampaignEvidence(campaign_id=92,result_id=3))
        db.add(EvidenceAssessment(campaign_id=92,result_id=3,assessment_version=1,
            relevance_label='RELEVANT',sentiment='NEUTRAL',geographic_signals_json='[]'))
        db.commit()
        scoped=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91','paged':True,'include_totals':True})
        assert scoped['available_provinces']==['Riau','Sumatera Selatan']
        assert 'Jawa Timur' not in scoped['available_provinces']
        # The options still reflect ALL eligible posts, not only selected province.
        filtered=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91','paged':True,'include_totals':True,
             'province_filter':'Sumatera Selatan'})
        assert filtered['available_provinces']==scoped['available_provinces']
        assert [row['id'] for row in filtered['findings']]==['2']
        assert filtered['findings'][0]['source_provinces']==['Sumatera Selatan']
        all_campaigns=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'paged':True,'include_totals':True})
        assert set(all_campaigns['available_provinces'])=={
            'Jawa Timur','Riau','Sumatera Selatan'}
        # Zero posts means no option, even though the national dictionary knows it.
        assert 'Bali' not in all_campaigns['available_provinces']
    finally:db.close()


def test_province_dropdown_excludes_irrelevant_and_partial_word_mentions():
    from app.inbox_provinces import matching_source_provinces
    assert matching_source_provinces('Kami kembali ke rumah dan melanjutkan diskusi')==[]
    assert matching_source_provinces('Dugaan kasus di Kabupaten Musi Banyuasin')==['Sumatera Selatan']
    db=fixture()
    try:
        db.add(SocialListeningResult(id=2,run_id=1,platform='instagram',
            author_name='Reporter',text_content='Pemilu di Bali perlu dibahas',
            published_at='2026-11-10T00:00:00Z'))
        db.add(CampaignEvidence(campaign_id=91,result_id=2))
        db.add(EvidenceAssessment(campaign_id=91,result_id=2,assessment_version=1,
            relevance_label='IRRELEVANT',sentiment='NEUTRAL'))
        db.commit()
        data=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91','paged':True,'include_totals':True})
        assert data['available_provinces']==['Riau']
        zero=campaign_action(db,user(),'campaignIntelligenceInbox',
            {'campaign_id':'91','paged':True,'include_totals':True,
             'province_filter':'Bali'})
        assert zero['findings']==[]
        assert zero['full_statistics']['posts']==0
        assert zero['available_provinces']==['Riau']
    finally:db.close()
