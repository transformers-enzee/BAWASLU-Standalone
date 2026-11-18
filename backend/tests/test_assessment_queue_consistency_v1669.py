"""v166.9: a pending job with an existing valid assessment is never claimable."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import CampaignEvidence,AIAssessmentJob,EvidenceAssessment,SocialListeningResult
from app.campaign_ai_readiness import campaign_ai_worker_readiness,campaign_manual_batch_preview
from app.assessment_operations_overview import campaign_assessment_operations_overview

def fixture():
    eng=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(eng)
    return eng,Session(eng)

def put(db,cid,rid,latest=None,state='PENDING',text='evidence',method='KEYWORD'):
    db.add(CampaignEvidence(campaign_id=cid,result_id=rid,match_method=method))
    db.add(SocialListeningResult(id=rid,run_id=1,text_content=text))
    db.add(AIAssessmentJob(campaign_id=cid,result_id=rid,state=state,attempts=0))
    if latest:
        for i,label in enumerate(latest,1):
            db.add(EvidenceAssessment(campaign_id=cid,result_id=rid,
                assessment_version=i,relevance_label=label))
    db.flush()

def test_claimable_matches_manual_preview_after_human_classification():
    eng,db=fixture()
    try:
        put(db,2,1,latest=['RELEVANT'])
        put(db,2,2,latest=['RELEVANT','UNASSESSED'])
        put(db,2,3,latest=['UNASSESSED','IRRELEVANT'])
        put(db,2,4)
        put(db,2,5,text='   ')
        put(db,2,6,latest=['RELEVANT'],method='WATCHLIST_ACCOUNT')
        put(db,3,7,latest=['RELEVANT'])
        q=campaign_ai_worker_readiness(db,2,env={})
        p=campaign_manual_batch_preview(db,2,10,env={})
        assert q['queue_counts']['pending']==5
        assert q['queue_counts']['claimable_pending_with_text']==2
        assert q['queue_counts']['pending_missing_source_or_text']==1
        assert q['pending_already_assessed_excluded_from_ai']==2
        assert p['eligible_queued_unassessed']==2
        overview=campaign_assessment_operations_overview(db,2)
        assert [x['code'] for x in overview['issues']]==['PENDING_ALREADY_ASSESSED']
        assert overview['automatic_ai_authorized'] is False
        assert overview['database_writes']==0 and not overview['paid_provider_called']
    finally:db.close();eng.dispose()

def test_only_newest_label_decides_eligibility():
    eng,db=fixture()
    try:
        put(db,4,1,latest=['RELEVANT','UNASSESSED'])
        put(db,4,2,latest=['UNASSESSED','UNCERTAIN'])
        result=campaign_ai_worker_readiness(db,4,env={})
        assert result['queue_counts']['claimable_pending_with_text']==1
        assert result['pending_already_assessed_excluded_from_ai']==1
    finally:db.close();eng.dispose()
