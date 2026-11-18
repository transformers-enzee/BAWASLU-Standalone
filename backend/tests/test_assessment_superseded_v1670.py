"""v167.0 no-credit supersession must retain original provenance."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment
from app.assessment_superseded_reconcile import superseded_preview,apply_superseded_reconciliation
from app.campaign_ai_readiness import campaign_ai_worker_readiness
from app.assessment_completion_audit import campaign_completion_audit

def fixture():
    e=create_engine('sqlite:///:memory:');Base.metadata.create_all(e);return e,Session(e)

def add(db,cid,rid,labels=None,state='PENDING',kind='KEYWORD'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=kind))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=0))
    for i,label in enumerate(labels or [],1):
        db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
            assessment_version=i,relevance_label=label))
    db.flush()

def test_bounded_idempotent_reconciliation_does_not_forge_completion():
    e,db=fixture()
    try:
        add(db,4,1,['RELEVANT']);add(db,4,2,['UNASSESSED','IRRELEVANT'])
        add(db,4,3,['RELEVANT','UNASSESSED']);add(db,4,4)
        add(db,4,5,['UNCERTAIN'],state='PROCESSING')
        add(db,4,6,['RELEVANT'],kind='WATCHLIST_ACCOUNT')
        add(db,2,7,['RELEVANT'])
        before=db.query(EvidenceAssessment).count()
        assert superseded_preview(db,4)['already_assessed_pending_jobs']==2
        assert apply_superseded_reconciliation(db,4,1)['superseded_jobs']==1
        assert apply_superseded_reconciliation(db,4)['superseded_jobs']==1
        assert apply_superseded_reconciliation(db,4)['superseded_jobs']==0
        assert db.query(EvidenceAssessment).count()==before
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,state='SUPERSEDED_ASSESSED').count()==2
        assert db.query(AIAssessmentJob).filter_by(campaign_id=4,state='PENDING').count()==2
        assert campaign_ai_worker_readiness(db,4,env={})['queue_counts']['superseded_assessed']==2
        audit=campaign_completion_audit(db,4)
        assert audit['superseded_assessed_jobs']==2
        assert audit['completed_jobs']==0 and audit['counts_reconciled']
    finally:db.close();e.dispose()

def test_confirmation_and_invalid_limits():
    from pathlib import Path
    root=Path(__file__).parents[1]/'app'
    c=(root/'campaigns.py').read_text()
    s=(root/'socialcrawl.py').read_text()
    assert "if (data or {}).get('confirm_no_credit_supersede') is not True:" in c
    assert "if not _editable(p,campaign):" in c
    assert "'campaignAssessmentSupersededApply'" in s
    e,db=fixture()
    try:
        for v in (0,101,True,'10'):
            try:apply_superseded_reconciliation(db,4,v)
            except ValueError:pass
            else:assert False,v
    finally:db.close();e.dispose()
