"""v166.7 status semantics, snapshot transparency and campaign-switch request guards."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob
from app.assessment_operations_overview import campaign_assessment_operations_overview

def setup():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def put(db,cid,rid,state=None):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method='KEYWORD'))
    if state is not None:
        db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=0))
    db.flush()

def test_pending_queue_is_not_mislabeled_as_fully_complete():
    engine,db=setup()
    try:
        put(db,2,1,'PENDING')
        o=campaign_assessment_operations_overview(db,2)
        assert o['lifecycle_status']=='AWAITING_PROCESSING'
        assert o['review_required'] is False
        assert o['snapshot_is_atomic'] is False
        assert o['generated_at_utc'].endswith('+00:00')
        assert o['automatic_ai_authorized'] is False
        assert o['database_writes']==0
    finally:db.close();engine.dispose()

def test_unqueued_work_is_flagged_for_review_not_automatically_started():
    engine,db=setup()
    try:
        put(db,2,1)
        o=campaign_assessment_operations_overview(db,2)
        assert o['lifecycle_status']=='REVIEW_REQUIRED'
        assert [x['code'] for x in o['issues']]==['UNQUEUED_EVIDENCE']
        assert o['paid_provider_called'] is False
    finally:db.close();engine.dispose()

def test_empty_campaign_has_no_exceptions_but_does_not_authorize_ai():
    engine,db=setup()
    try:
        o=campaign_assessment_operations_overview(db,2)
        assert o['lifecycle_status']=='NO_EXCEPTIONS'
        assert o['assessment_link_coverage']['monitoring_evidence_links']==0
        assert not o['automatic_ai_authorized']
    finally:db.close();engine.dispose()

def test_ui_ignores_late_responses_after_campaign_switch():
    from pathlib import Path
    src=(Path(__file__).parents[2]/'frontend'/'src'/'components'/'intel'/'AssessmentOperationsPanel.jsx').read_text()
    parent=(Path(__file__).parents[2]/'frontend'/'src'/'components'/'intel'/'CampaignPanel.jsx').read_text()
    assert "requestToken.current+=1" in src
    assert "activeCampaign.current===requestedCampaign" in src
    assert "if(stillCurrent())setData(r.data||null)" in src
    assert "if(stillCurrent())setBusy(false)" in src
    assert "<AssessmentOperationsPanel key={selected.id} campaignId={selected.id} />" in parent
    assert "not an atomic snapshot" in src
