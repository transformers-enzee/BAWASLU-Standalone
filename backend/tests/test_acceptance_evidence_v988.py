"""Acceptance batch: authorized pre-save group evidence and signed-label QA gates."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.access import default_permissions
from app.campaigns import campaign_action
from app.qa_saved_accuracy import REFERENCE_SIGNOFF_QUERY,REVIEWED_ACCURACY_QUERY

def officer():
    return {'id':'11','role':'National Administrator','status':'Active',
        'geographic_scope':'Nationwide',
        'permissions':default_permissions('National Administrator')}

def database():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=91,name='Acceptance',created_by='11',
        primary_keywords_json='[]',secondary_keywords_json='[]',
        excluded_keywords_json='[]'))
    for i,text in [(1,'Dugaan pemilu dibahas oleh warga'),
                   (2,'Dugaan pemilu dibahas oleh warga')]:
        db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
            author_name='Observer '+str(i),text_content=text,
            canonical_url='https://example.test/'+str(i)))
        db.add(CampaignEvidence(campaign_id=91,result_id=i))
    db.commit()
    return db

def test_duplicate_pre_save_evidence_has_authorized_sources_but_no_review_writes():
    db=database()
    try:
        result=campaign_action(db,officer(),'campaignFindingGroupsPreview',{},'91')
        assert result['proposal_count']==1
        assert result['proposals'][0]['type']=='EXACT_DUPLICATE'
        assert result['preview_contains_only_authorized_source_excerpts'] is True
        evidence=result['proposal_evidence'][0]
        assert evidence['type']=='EXACT_DUPLICATE'
        assert len(evidence['sources'])==2
        assert all(x['text_excerpt']=='Dugaan pemilu dibahas oleh warga' for x in evidence['sources'])
        assert all(x['relevance_label']=='NOT_REQUIRED_FOR_EXACT_DUPLICATE'
                   for x in evidence['sources'])
        assert all(x['canonical_url'].startswith('https://example.test/')
                   for x in evidence['sources'])
        assert result['paid_provider_called'] is False
        assert db.query(EvidenceAssessment).count()==0
    finally: db.close()

def test_pre_save_preview_respects_campaign_source_scope():
    db=database()
    try:
        db.query(CampaignEvidence).filter_by(result_id=2).delete()
        db.commit()
        result=campaign_action(db,officer(),'campaignFindingGroupsPreview',{},'91')
        assert result['proposal_count']==0
        assert result['proposal_evidence']==[]
    finally: db.close()

def test_qa_signoff_uses_real_analyst_decisions_not_import_review_status():
    signed=str(REFERENCE_SIGNOFF_QUERY)
    reviewed=str(REVIEWED_ACCURACY_QUERY)
    for source in (signed,reviewed):
        assert 'qa_alignment_decisions' in source
        assert "('confirmed','corrected')" in source
        assert "source_relation='distinct_comments'" in source
    assert "NOT ILIKE '%holdout%'" in reviewed
    assert 'GROUP BY prompt_version,model' in reviewed
    assert 'qa_alignment_decisions' not in 'historical_score_rewrite'

def test_reviewed_qa_summary_never_promotes_missing_or_unsigned_labels():
    from app.qa_saved_accuracy import summarize_version_stats
    historical=summarize_version_stats([{
       'prompt_version':'v17','model':'mock','evaluated':33,
       'correct':20,'missing_prediction':0,'unsigned_labels':33}])
    assert historical[0]['accuracy_percent']==60.6
    assert historical[0]['accuracy_target_met'] is False
