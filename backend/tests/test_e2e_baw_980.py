"""No-cost end-to-end acceptance for candidate, duplicates, narratives, review and jurisdiction."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign,SocialListeningResult,CampaignEvidence,
                        EvidenceAssessment,WatchlistItem,CampaignFindingGroup)
from app.access import default_permissions
from app.campaigns import campaign_action
from app.saved_assessment_views import saved_classifications_for_posts
from app.jurisdiction_review import jurisdiction_action,jurisdiction_status

def officer(role='National Administrator'):
    return {'id':'11','role':role,'geographic_scope':'Nationwide',
            'status':'Active','permissions':default_permissions(role)}

def database():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=91,name='BAWASLU testing',created_by='11',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    rows=[
        (1,'Daftar pemilih dipertanyakan oleh warga di TPS A','RELEVANT'),
        (2,'Daftar pemilih perlu pemutakhiran di TPS B','RELEVANT'),
        (3,'Daftar pemilih dalam pembahasan pemilu di TPS C','RELEVANT'),
        (4,'Pemeriksaan formulir laporan pemilu hari ini',None),
        (5,'Pemeriksaan formulir laporan pemilu hari ini',None)]
    for i,body,label in rows:
        db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
            text_content=body,author_name='Reporter '+str(i),
            canonical_url='https://example.test/'+str(i),
            published_at='2026-10-03T08:00:00Z'))
        db.add(CampaignEvidence(campaign_id=91,result_id=i))
        if label:
            db.add(EvidenceAssessment(campaign_id=91,result_id=i,
                assessment_version=1,relevance_label=label,sentiment='NEUTRAL'))
    db.commit()
    return db

def test_duplicate_unassessed_posts_and_narratives_complete_full_review_cycle():
    db=database()
    try:
        preview=campaign_action(db,officer(),'campaignFindingGroupsPreview',{},'91')
        assert preview['exact_duplicate_source_posts']==5
        types={item['type'] for item in preview['proposals']}
        assert {'EXACT_DUPLICATE','NARRATIVE_CANDIDATE'} <= types
        assert preview['readiness']['unassessed_posts']==2
        assert preview['paid_provider_called'] is False
        saved=campaign_action(db,officer(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        assert saved['newly_saved']>=2
        listing=campaign_action(db,officer(),'campaignFindingGroupsList',{},'91')
        assert listing['count']>=2
        for group in listing['groups']:
            evidence=campaign_action(db,officer(),'campaignFindingGroupSources',
                {'group_id':group['id']},'91')
            assert evidence['source_count']==len(group['source_ids'])
            assert evidence['legal_violation_confirmed'] is False
            if group['group_type']=='EXACT_DUPLICATE':
                assert all(s['relevance_label']=='UNASSESSED' for s in evidence['sources'])
            decision=campaign_action(db,officer(),'campaignFindingGroupsReview',
                {'group_id':group['id'],'decision':'ACCEPTED',
                 'rationale':'I inspected the source texts, authors and evidence for this grouping.'},'91')
            assert decision['group']['review_status']=='ACCEPTED'
        assert campaign_action(db,officer(),'campaignFindingGroupsList',
            {},'91')['accepted_count']>=2
        assert campaign_action(db,officer(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')['newly_saved']==0
    finally:db.close()

def test_group_source_data_cannot_be_read_by_out_of_scope_principal():
    db=database()
    try:
        listing=campaign_action(db,officer(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        group_id=listing['saved_group_ids'][0]
        db.query(CampaignEvidence).filter_by(campaign_id=91,result_id=4).delete()
        db.commit()
        with pytest.raises(PermissionError):
            campaign_action(db,officer(),'campaignFindingGroupSources',
                {'group_id':group_id},'999')
    finally:db.close()

def test_saved_views_reuse_source_full_name_without_duplicate_canonical_ids():
    db=database()
    try:
        db.add(WatchlistItem(name='Andika Pratama',type='Candidate',
            status='Active',priority='Medium',candidate_aliases_json='[]'))
        post=db.get(SocialListeningResult,1)
        post.text_content+=' Andika Pratama hadir.'
        assessment=db.query(EvidenceAssessment).filter_by(result_id=1).first()
        assessment.candidate_signals_json='["Andika Pratama"]'
        db.commit()
        inbox=campaign_action(db,officer(),'campaignIntelligenceInbox',
            {'campaign_id':'91'})
        row=next(x for x in inbox['findings'] if x['id']=='1')
        assert row['canonical_candidate_ids']==['candidate:1']
        shared=saved_classifications_for_posts(db,officer(),[post])[1][0]
        assert shared['candidate_classification']=='MATCHED'
        assert [x['canonical_candidate_id'] for x in
            shared['candidate_identity_matches']]==['candidate:1']
    finally:db.close()

def test_verified_jurisdiction_is_revoked_if_latest_assessment_becomes_irrelevant():
    db=database()
    try:
        post=db.get(SocialListeningResult,1)
        post.text_content='Dugaan pelanggaran di Riau terkait daftar pemilih'
        db.commit()
        jurisdiction_action(db,officer(),'campaignJurisdictionReview',
            {'result_id':'1','decision':'CONFIRMED','province':'Riau',
             'rationale':'The source explicitly locates this suspected incident in Riau.'},'91')
        assert jurisdiction_status(db,91,1,post)['incident_jurisdiction_verified'] is True
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,
            assessment_version=2,relevance_label='IRRELEVANT'))
        db.commit()
        status=jurisdiction_status(db,91,1,post)
        assert status['decision']=='STALE_RELEVANCE_CHANGED'
        assert status['incident_jurisdiction_verified'] is False
    finally:db.close()

def test_inbox_has_complete_source_review_actions_without_credit_spending():
    from pathlib import Path
    frontend=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    for action in ('campaignFindingGroupsPreview','campaignFindingGroupsSave',
                   'campaignFindingGroupSources','campaignFindingGroupsReview'):
        assert action in frontend
    assert 'View all group evidence' in frontend
    assert 'Open original source' in frontend
