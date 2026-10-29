"""Source freshness and conservative acceptance tests for saved grouping."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.access import default_permissions
from app.finding_groups import finding_group_action

def actor():
    return {'id':'11','status':'Active','role':'National Administrator',
            'geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}

def fixture():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=44,name='Test',created_by='11',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    for i in (1,2,3):
        db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
            text_content='Warga mempertanyakan daftar pemilih pada tahapan pemilu '+str(i),
            author_name='Reporter '+str(i),canonical_url='https://example.org/'+str(i),
            published_at='2026-10-01T12:00:00Z'))
        db.add(CampaignEvidence(campaign_id=44,result_id=i))
        db.add(EvidenceAssessment(campaign_id=44,result_id=i,
            relevance_label='RELEVANT',assessment_version=1))
    db.commit()
    return db

def test_stale_narrative_cannot_be_accepted_after_source_edit():
    db=fixture()
    try:
        saved=finding_group_action(db,actor(),'campaignFindingGroupsSave',
            {'confirm_save':True},'44')
        assert saved['newly_saved']>=1
        db.get(SocialListeningResult,1).text_content='Unrelated sports report'
        db.commit()
        with pytest.raises(ValueError,match='stale'):
            finding_group_action(db,actor(),'campaignFindingGroupsReview',
                {'group_id':saved['saved_group_ids'][0],'decision':'ACCEPTED',
                 'rationale':'All source posts refer to one pattern.'},'44')
    finally:db.close()

def test_stale_group_cannot_be_accepted_after_relevance_reversal():
    db=fixture()
    try:
        saved=finding_group_action(db,actor(),'campaignFindingGroupsSave',
            {'confirm_save':True},'44')
        db.add(EvidenceAssessment(campaign_id=44,result_id=1,
            relevance_label='IRRELEVANT',assessment_version=2))
        db.commit()
        with pytest.raises(ValueError,match='stale'):
            finding_group_action(db,actor(),'campaignFindingGroupsReview',
                {'group_id':saved['saved_group_ids'][0],'decision':'ACCEPTED',
                 'rationale':'Grouping should be checked after reassessment.'},'44')
    finally:db.close()

def test_unchanged_proposal_still_accepts_with_auditable_rationale():
    db=fixture()
    try:
        saved=finding_group_action(db,actor(),'campaignFindingGroupsSave',
            {'confirm_save':True},'44')
        accepted=finding_group_action(db,actor(),'campaignFindingGroupsReview',
            {'group_id':saved['saved_group_ids'][0],'decision':'ACCEPTED',
             'rationale':'Three independent accounts discuss the same voter list theme.'},'44')
        assert accepted['group']['review_status']=='ACCEPTED'
        assert accepted['group']['legal_violation_confirmed'] is False
    finally:db.close()
