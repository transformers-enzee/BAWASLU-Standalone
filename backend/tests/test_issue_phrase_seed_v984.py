"""Starter phrases only on empty catalog; all detections remain provisional."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (IssueCategory,IssueCategoryPhrase,MonitoringCampaign,
    SocialListeningResult,CampaignEvidence,EvidenceAssessment,EvidenceReview)
from app.issue_phrase_seed import seed_default_issue_phrases,STARTER_PHRASES
from app.campaigns import campaign_action
from app.access import default_permissions

def actor():
    return {'id':'11','role':'National Administrator','status':'Active',
        'geographic_scope':'Nationwide',
        'permissions':default_permissions('National Administrator')}

def fixture():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    for i,name in enumerate(STARTER_PHRASES,1):
        db.add(IssueCategory(id=i,name=name,active=True))
    db.commit()
    return db

def test_seed_initializes_active_phrases_only_once():
    db=fixture()
    try:
        with db.begin():
            created=seed_default_issue_phrases(db.connection())
        assert created==10
        assert db.query(IssueCategoryPhrase).count()==10
        assert all(row.active for row in db.query(IssueCategoryPhrase))
        with db.begin():
            assert seed_default_issue_phrases(db.connection())==0
        assert db.query(IssueCategoryPhrase).count()==10
    finally:db.close()

def test_configured_admin_vocabulary_is_never_overwritten():
    db=fixture()
    try:
        db.add(IssueCategoryPhrase(category_id=4,phrase='Officer disabled keyword',
            normalized_phrase='officer disabled keyword',active=False))
        db.commit()
        with db.begin():
            assert seed_default_issue_phrases(db.connection())==0
        assert db.query(IssueCategoryPhrase).count()==1
    finally:db.close()

def test_seeded_phrase_creates_human_lead_not_automatic_violation():
    db=fixture()
    try:
        with db.begin():
            seed_default_issue_phrases(db.connection())
        db.add(MonitoringCampaign(id=91,name='Oversight',created_by='11',
            primary_keywords_json='[]',secondary_keywords_json='[]',
            excluded_keywords_json='[]'))
        db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
            text_content='Warga melaporkan dugaan politik uang dalam pemilu.',
            author_name='Reporter',canonical_url='https://example.test/1'))
        db.add(CampaignEvidence(campaign_id=91,result_id=1))
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,
            assessment_version=1,relevance_label='RELEVANT',sentiment='NEGATIVE',
            potential_issue_signals_json='[]'))
        db.commit()
        inbox=campaign_action(db,actor(),'campaignIntelligenceInbox',
            {'campaign_id':'91'})
        post=inbox['findings'][0]
        assert post['issue_review_leads']
        assert post['issue_review_leads'][0]['signal_provenance']=='KEYWORD_SCREENING'
        assert post['issue_review_leads'][0]['category_name']=='Electoral Violation'
        assert post['potential_issues']==[]
        assert not post['is_flagged']
        assert inbox['classification_processing']['intelligence_players']['Potential Violations']['count']==0
        assert db.query(EvidenceReview).count()==0
        assert inbox['paid_provider_called'] is False
    finally:db.close()
