"""v167.2 verifies superseded status cannot silently return to billable queue."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import AIAssessmentJob,CampaignEvidence,EvidenceAssessment
from app.assessment_superseded_reconcile import superseded_preview,apply_superseded_reconciliation
from app.assessment_operations_overview import campaign_assessment_operations_overview
from app.assessment_interrupted_recovery import interrupted_campaign_preview

def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine,Session(engine)

def add(db,cid,rid,label,state='PENDING',kind='KEYWORD'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=0))
    if label:
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
            assessment_version=1,relevance_label=label))
    db.flush()

def test_superseded_after_new_human_unassessed_version_is_review_only():
    engine,db=fixture()
    try:
        add(db,4,1,'RELEVANT')
        add(db,4,2,'IRRELEVANT')
        add(db,4,3,'RELEVANT',kind='WATCHLIST_ACCOUNT')
        add(db,5,4,'RELEVANT')
        assert apply_superseded_reconciliation(db,4)['superseded_jobs']==2
        db.add(EvidenceAssessment(campaign_id=4,result_id=1,
            assessment_version=2,relevance_label='UNASSESSED'))
        db.flush()
        preview=superseded_preview(db,4)
        assert preview['superseded_assessed_jobs']==2
        assert preview['superseded_without_current_classification']==1
        assert preview['superseded_needing_manual_review'] is True
        assert preview['superseded_automatically_reopened'] is False
        assert preview['already_assessed_pending_jobs']==0
        o=campaign_assessment_operations_overview(db,4)
        assert [i['code'] for i in o['issues']]==['SUPERSEDED_CLASSIFICATION_CHANGED']
        assert o['paid_provider_called'] is False and o['database_writes']==0
        assert interrupted_campaign_preview(db,4)['superseded_assessed_jobs']==2
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,state='PENDING').count()==1  # excluded watchlist only
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,state='SUPERSEDED_ASSESSED').count()==2
        assert db.query(AIAssessmentJob).filter_by(campaign_id=5,state='PENDING').count()==1
    finally:db.close();engine.dispose()

def test_superseded_missing_assessment_is_not_automatically_resumed():
    engine,db=fixture()
    try:
        add(db,3,1,None,state='SUPERSEDED_ASSESSED')
        p=superseded_preview(db,3)
        assert p['superseded_without_current_classification']==1
        assert p['recorded_provider_usage_unchanged'] is True
        assert db.query(AIAssessmentJob).first().state=='SUPERSEDED_ASSESSED'
    finally:db.close();engine.dispose()
