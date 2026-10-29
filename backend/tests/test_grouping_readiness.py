"""Saved-evidence acceptance readiness must distinguish missing classification from no findings."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.access import default_permissions
from app.models import MonitoringCampaign,CampaignEvidence,SocialListeningResult,EvidenceAssessment
from app.finding_groups import finding_group_action

def user():
    return {'id':'1','status':'Active','role':'National Administrator',
            'geographic_scope':'Nationwide',
            'permissions':default_permissions('National Administrator')}

def setup():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=17,name='Test',created_by='1',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    for i in range(1,5):
        db.add(SocialListeningResult(id=i,run_id=1,platform='x',
            text_content='Daftar pemilih di Riau diperiksa '+str(i),
            canonical_url='https://test.org/'+str(i),author_name='Reporter'+str(i)))
        db.add(CampaignEvidence(campaign_id=17,result_id=i))
    db.add(EvidenceAssessment(campaign_id=17,result_id=1,
        assessment_version=1,relevance_label='RELEVANT'))
    db.commit()
    return db

def test_missing_assessments_are_backlog_not_negative_findings():
    db=setup()
    try:
        result=finding_group_action(db,user(),'campaignFindingGroupsReadiness',{},'17')
        assert result['linked_posts']==4
        assert result['relevant_posts']==1
        assert result['unassessed_posts']==3
        assert result['status']=='NEEDS_RELEVANCE_ASSESSMENTS'
        assert result['zero_group_result_is_conclusive'] is False
        assert result['paid_provider_called'] is False
        preview=finding_group_action(db,user(),'campaignFindingGroupsPreview',{},'17')
        assert preview['readiness']['unassessed_posts']==3
        assert preview['proposal_count']==0
        assert preview['zero_group_result_is_conclusive'] is False
    finally:db.close()

def test_fully_classified_scope_can_return_valid_empty_result():
    db=setup()
    try:
        for i in (2,3,4):
            db.add(EvidenceAssessment(campaign_id=17,result_id=i,
                assessment_version=1,relevance_label='IRRELEVANT'))
        db.commit()
        result=finding_group_action(db,user(),'campaignFindingGroupsReadiness',{},'17')
        assert result['unassessed_posts']==0
        assert result['zero_group_result_is_conclusive'] is True
        assert result['candidate_identity_required'] is False
    finally:db.close()
