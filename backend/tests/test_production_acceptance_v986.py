"""Role-scoped production acceptance, no fabricated officer decisions."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment,CampaignFindingGroup
from app.access import default_permissions
from app.campaigns import campaign_action

def officer(role='National Administrator'):
    return {'id':'11','role':role,'status':'Active',
            'geographic_scope':'Nationwide','permissions':default_permissions(role)}

def fixture():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=91,name='QA Campaign',created_by='11',
        primary_keywords_json='[]',secondary_keywords_json='[]',
        excluded_keywords_json='[]'))
    data=[
      (1,'Daftar pemilih dipertanyakan oleh warga di TPS A','RELEVANT'),
      (2,'Daftar pemilih dipertanyakan oleh warga di TPS B','RELEVANT'),
      (3,'Daftar pemilih dipertanyakan oleh warga di TPS C','RELEVANT'),
      (4,'Rapat pemilu di wilayah setempat',None),
      (5,'Rapat pemilu di wilayah setempat',None)]
    for i,body,label in data:
        db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
            text_content=body,author_name='Reporter '+str(i),
            canonical_url='https://example.test/'+str(i),
            published_at='2026-10-29T03:00:00Z'))
        db.add(CampaignEvidence(campaign_id=91,result_id=i))
        if label:db.add(EvidenceAssessment(campaign_id=91,result_id=i,
            assessment_version=1,relevance_label=label,sentiment='NEUTRAL'))
    db.commit()
    return db

def test_acceptance_shows_real_group_proposals_without_claiming_signoff():
    db=fixture()
    try:
        result=campaign_action(db,officer(),'campaignAcceptanceSnapshot',{},'91')
        assert result['linked_posts']==5
        assert result['unassessed_posts']==2
        assert result['group_proposals_by_type']['EXACT_DUPLICATE']==1
        assert result['saved_groups_count']==0
        assert result['officer_accepted_groups']==0
        assert result['does_not_record_formal_signoff'] is True
        assert result['paid_provider_called'] is False
        states={row['number']:row for row in result['items']}
        assert len(states)==15
        assert states[8]['production_state']=='PROPOSALS_READY_TO_SAVE'
        assert states[14]['production_state']=='TARGET_NOT_MET'
        assert all(not row['officer_signoff_inferred'] for row in states.values())
        assert db.query(CampaignFindingGroup).count()==0
    finally:db.close()

def test_saved_group_remains_pending_until_officer_reviews_it():
    db=fixture()
    try:
        saved=campaign_action(db,officer(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        assert saved['newly_saved']>=1
        before=db.query(CampaignFindingGroup).count()
        snapshot=campaign_action(db,officer(),'campaignAcceptanceSnapshot',{},'91')
        row=next(x for x in snapshot['items'] if x['number']==8)
        assert row['production_state']=='SAVED_PENDING_OFFICER_REVIEW'
        assert snapshot['officer_accepted_groups']==0
        assert db.query(CampaignFindingGroup).count()==before
    finally:db.close()

def test_cross_campaign_scope_denied_for_nonexistent_campaign():
    db=fixture()
    try:
        with pytest.raises(PermissionError):
            campaign_action(db,officer('Viewer'),'campaignAcceptanceSnapshot',{},'999')
    finally:db.close()

def test_frontend_displays_acceptance_evidence_and_confusions():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    for token in ('campaignAcceptanceSnapshot',
       'Load production acceptance evidence (free)',
       'No item below represents formal officer sign-off',
       'Most common saved category confusions'):
        assert token in source
