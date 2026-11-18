"""v168.7: cross-module continuity uses real persisted links, not inferred acceptance."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (SocialListeningResult,CampaignEvidence,MonitoringCampaign,
    IntelligenceItem,EvidenceAssessment)
from app.casework import CaseAssignment,CaseReport
from app.assistant_knowledge import KnowledgePDF,KnowledgeChunk
from app.module_acceptance_evidence import module_acceptance_evidence

def seeded():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    db.add(MonitoringCampaign(id=30,name='Synthetic Campaign',created_by='1',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
        text_content='Test electoral operation evidence',canonical_url='https://example.invalid/source'))
    db.add(CampaignEvidence(campaign_id=30,result_id=1,match_method='KEYWORD'))
    db.flush()
    return engine,db

def test_integrity_when_social_links_and_promotion_exist():
    e,db=seeded()
    try:
        good=module_acceptance_evidence(db)
        assert good['cross_module_link_checks_run']==4
        assert good['cross_module_link_checks_passed']==4
        assert good['counts']['orphan_campaign_source_links']==0
        assert good['counts']['orphan_inbox_promotions']==0
        assert not good['cross_module_link_integrity_is_not_functional_uat'] is False
        assert good['automatically_verified_cross_module_e2e'] is False
    finally:db.close();e.dispose()

def test_orphan_social_source_link_detected_without_leaking_id():
    e,db=seeded()
    try:
        db.add(CampaignEvidence(campaign_id=30,result_id=999,match_method='KEYWORD'))
        db.flush()
        result=module_acceptance_evidence(db)
        assert result['counts']['orphan_campaign_source_links']==1
        assert result['cross_module_link_integrity'][0]['integrity']=='REVIEW_REQUIRED'
        assert result['cross_module_link_checks_passed']==3
        assert '999' not in str(result)
        assert result['database_writes']==0
    finally:db.close();e.dispose()

def test_orphan_promotion_detected_without_source_content():
    e,db=seeded()
    try:
        row=db.get(SocialListeningResult,1)
        row.promoted_intelligence_id=972
        db.flush()
        r=module_acceptance_evidence(db)
        assert r['counts']['orphan_inbox_promotions']==1
        assert r['cross_module_link_integrity'][1]['integrity']=='REVIEW_REQUIRED'
        assert 'https://example.invalid/source' not in str(r)
    finally:db.close();e.dispose()

def test_casework_reporting_links_checked_and_orphans_flagged():
    e,db=seeded()
    try:
        db.add(CaseReport(case_id=925,created_by=1))
        db.flush()
        r=module_acceptance_evidence(db)
        assert r['counts']['orphan_case_reports']==1
        assert r['cross_module_link_integrity'][3]['broken_links']==1
        assert not r['formal_client_acceptance_recorded']
    finally:db.close();e.dispose()

def test_knowledge_chunks_link_to_existing_document():
    e,db=seeded()
    try:
        db.add(KnowledgeChunk(document_id=950,page_number=1,text_content='Synthetic corpus'))
        db.flush()
        r=module_acceptance_evidence(db)
        assert r['counts']['orphan_knowledge_chunks']==1
        assert r['cross_module_link_integrity'][2]['integrity']=='REVIEW_REQUIRED'
    finally:db.close();e.dispose()
