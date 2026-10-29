"""Human-source-cue escalation: full detection-to-officer-review lifecycle, no AI."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign, SocialListeningResult, CampaignEvidence,
                        EvidenceAssessment, EvidenceReview, IssueCategory, IssueCategoryPhrase)
from app.access import default_permissions
from app.campaigns import campaign_action

TEXT='Sejumlah warga melaporkan dugaan politik uang menjelang pemilu.'
def principal(role='National Administrator'):
    return {'id':'11','role':role,'status':'Active','geographic_scope':'Nationwide',
            'permissions':default_permissions(role)}

def setup():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=91,name='QA',created_by='11',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
        author_name='Reporter',text_content=TEXT,
        canonical_url='https://example.test/post/1',
        published_at='2026-10-29T01:00:00Z'))
    db.add(CampaignEvidence(campaign_id=91,result_id=1))
    db.add(EvidenceAssessment(campaign_id=91,result_id=1,
        assessment_version=1,relevance_label='RELEVANT',sentiment='NEUTRAL',
        potential_issue_signals_json='[]'))
    db.add(IssueCategory(id=7,name='Campaign Finance',active=True))
    db.add(IssueCategoryPhrase(category_id=7,phrase='politik uang',
        normalized_phrase='politik uang',active=True))
    db.commit()
    return db

def test_keyword_cue_to_source_verified_manual_flag_and_dismissal():
    db=setup()
    try:
        inbox=campaign_action(db,principal(),'campaignIntelligenceInbox',
            {'campaign_id':'91'})
        row=inbox['findings'][0]
        assert row['potential_issues']==[]
        assert not row['is_flagged']
        assert inbox['classification_processing']['intelligence_players']['Potential Violations']['count']==0
        assert row['issue_review_leads']
        cue=row['issue_review_leads'][0]
        assert cue['category_id']==7
        assert cue['signal_provenance']=='KEYWORD_SCREENING'
        assert cue['evidence_quote'] in TEXT
        assert row['can_review_flag'] is True
        with pytest.raises(ValueError,match='Source quote'):
            campaign_action(db,principal(),'campaignManualFlag',{'result_id':'1',
                'assessment_version':1,'category_id':'7','rationale':'Human examination needed',
                'source_quote':'False fabricated quotation not in original'},'91')
        assert db.query(EvidenceReview).count()==0
        result=campaign_action(db,principal(),'campaignManualFlag',{
            'result_id':'1','assessment_version':1,'category_id':'7',
            'rationale':'Independent officer examination is required',
            'source_quote':cue['evidence_quote']},'91')
        assert result['source_quote_verified'] is True
        latest=db.query(EvidenceReview).one()
        assert latest.decision=='FURTHER_INVESTIGATION'
        assert cue['evidence_quote'] in latest.rationale
        flagged=campaign_action(db,principal(),'campaignIntelligenceInbox',
            {'campaign_id':'91'})['findings'][0]
        assert flagged['flag_review_status']=='FURTHER_INVESTIGATION'
        assert flagged['is_flagged'] is True
        assert len(flagged['flag_review_history'])==1
        review=campaign_action(db,principal(),'campaignFlagReview',{
            'result_id':'1','assessment_version':1,'decision':'FLAG_DISMISSED',
            'rationale':'Source checked independently, no issue substantiated.'},'91')
        assert review['saved']
        after=campaign_action(db,principal(),'campaignIntelligenceInbox',
            {'campaign_id':'91'})
        item=after['findings'][0]
        assert item['flag_review_status']=='FLAG_DISMISSED'
        assert item['is_flagged'] is False
        assert len(item['flag_review_history'])==2
        assert after['classification_processing']['intelligence_players']['Potential Violations']['count']==0
        assessment=db.query(EvidenceAssessment).one()
        assert assessment.sentiment=='NEUTRAL'
        assert assessment.potential_issue_signals_json=='[]'
        assert db.query(EvidenceReview).count()==2
    finally:db.close()

def test_quote_flag_authorization_stale_version_and_missing_evidence():
    db=setup()
    try:
        payload={'result_id':'1','assessment_version':1,'category_id':'7',
            'rationale':'This suspicious mention requires human examination',
            'source_quote':TEXT}
        with pytest.raises(PermissionError):
            campaign_action(db,principal('Viewer'),'campaignManualFlag',payload,'91')
        with pytest.raises(ValueError,match='Assessment changed'):
            campaign_action(db,principal(),'campaignManualFlag',
                {**payload,'assessment_version':0},'91')
        post=db.get(SocialListeningResult,1)
        post.text_content='Routine post without allegation'
        db.commit()
        with pytest.raises(ValueError,match='Source quote'):
            campaign_action(db,principal(),'campaignManualFlag',payload,'91')
        assert db.query(EvidenceReview).count()==0
    finally:db.close()

def test_frontend_cue_is_opt_in_and_human_rationale_is_not_generated():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    assert 'Escalate source cue for officer review' in source
    assert 'selectKeywordCueForReview(lead)' in source
    assert "setManualRationale('')" in source
    assert 'source_quote:verifiedCue' in source
    assert 'Your independent evidence assessment' in source
    assert 'await refreshReviewedPost(selected)' in source
