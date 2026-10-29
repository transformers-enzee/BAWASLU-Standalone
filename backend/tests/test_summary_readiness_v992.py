"""No-cost read-only summary readiness; never claim source extracts are AI."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.access import default_permissions
from app.campaigns import campaign_action

def test_real_saved_posts_without_ai_drafts_stay_pending():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        db.add(MonitoringCampaign(id=91,name='QA',created_by='11',
            primary_keywords_json='[]',secondary_keywords_json='[]',
            excluded_keywords_json='[]'))
        db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
            text_content='Warga mempertanyakan proses pemilu di TPS A'))
        db.add(CampaignEvidence(campaign_id=91,result_id=1))
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,
            assessment_version=1,relevance_label='RELEVANT',sentiment='NEUTRAL'))
        db.commit()
        actor={'id':'11','role':'National Administrator','status':'Active',
          'geographic_scope':'Nationwide',
          'permissions':default_permissions('National Administrator')}
        response=campaign_action(db,actor,'campaignSummaryReadiness',{},'91')
        assert response['posts_with_valid_saved_ai_drafts']==0
        assert response['posts_needing_ai_drafts']==1
        assert response['sources'][0]['source_excerpt_is_ai_summary'] is False
        assert response['suggested_small_pilot_ids']==['1']
        assert response['no_new_ai_called'] is True
        assert response['readiness_not_completion'] is True
    finally: db.close()

def test_summary_readiness_ui_is_explicitly_not_done():
    from pathlib import Path
    src=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    assert 'Inspect #12 AI summary readiness (free)' in src
    assert '#12 remains IN PROGRESS' in src
