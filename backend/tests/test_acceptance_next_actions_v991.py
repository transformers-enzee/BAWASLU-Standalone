"""Acceptance worklist must not fabricate human review or generated summaries."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence
from app.access import default_permissions
from app.campaigns import campaign_action

def test_actionable_duplicate_review_is_not_auto_saved():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        db.add(MonitoringCampaign(id=91,name='QA',created_by='11',
            primary_keywords_json='[]',secondary_keywords_json='[]',
            excluded_keywords_json='[]'))
        for i in (1,2):
            db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
                text_content='This is the same source text',author_name='Reporter'))
            db.add(CampaignEvidence(campaign_id=91,result_id=i))
        db.commit()
        p={'id':'11','role':'National Administrator','status':'Active',
          'geographic_scope':'Nationwide',
          'permissions':default_permissions('National Administrator')}
        response=campaign_action(db,p,'campaignAcceptanceSnapshot',{},'91')
        actions={x['item']:x for x in response['next_actions']}
        assert actions[8]['status']=='READY_FOR_OFFICER_TO_SAVE'
        assert actions[8]['source_groups']==1
        assert actions[9]['status']=='ASSESSMENT_COVERAGE_INCOMPLETE'
        assert actions[12]['status']=='NO_SAVED_AI_SUMMARIES'
        assert actions[14]['status']=='REFERENCE_SIGNOFF_AND_MEASURED_EVALUATION_REQUIRED'
        assert response['fully_completed_items_not_inferred'] is True
        assert response['paid_provider_called'] is False
    finally:db.close()

def test_acceptance_ui_never_claims_done_without_signoff():
    from pathlib import Path
    view=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    assert 'Unfinished production acceptance' in view
    assert 'Not marked DONE until all required evidence and approvals exist' in view
