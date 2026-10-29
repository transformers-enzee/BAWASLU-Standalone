"""Regression coverage for v95.6. AI is mocked; no charged requests."""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
    EvidenceAssessment,AIAssessmentJob,IssueCategory,IssueCategoryPhrase,EvidenceReview)
from app.access import default_permissions
from app.campaigns import campaign_action,_classify_campaign_sentiment
from app.saved_assessment_views import saved_classifications_for_posts


def officer():
    return {'id':'11','role':'National Administrator','status':'Active',
            'geographic_scope':'Nationwide',
            'permissions':default_permissions('National Administrator')}


def fixture(n=1):
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    db.add(MonitoringCampaign(id=91,name='Oversight',created_by='11',
        primary_keywords_json='["pemilu"]',secondary_keywords_json='[]',
        excluded_keywords_json='[]'))
    for i in range(1,n+1):
        db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
            author_name='Account',published_at='2026-10-29T01:00:00Z',
            text_content='Warga melaporkan dugaan politik uang dalam pemilu '+str(i)))
        db.add(CampaignEvidence(campaign_id=91,result_id=i))
    db.commit()
    return db


def fake_ai(monkeypatch,db,sentiment='NEGATIVE'):
    from app import auto_relevance
    monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
    monkeypatch.setenv('BAWASLU_AI_ASSESSMENTS_PER_RUN','20')
    monkeypatch.setattr(auto_relevance,'SessionLocal',lambda:Session(db.get_bind()))
    monkeypatch.setattr(auto_relevance,'reserve_automatic_ai_request',lambda *_:True)
    calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):
            return {'choices':[{'message':{'content':json.dumps({
                'relevance_label':'RELEVANT','confidence':'MEDIUM',
                'explanation':'Electoral oversight', 'sentiment':sentiment,
                'sentiment_confidence':'MEDIUM','sentiment_explanation':'Source tone',
                'gate_answers':[],'candidates':[],'locations':[],
                'reported_incident_signals':[],'potential_violation_signals':[],
                'issue_category_ids':[]})}}]}
    def post(*a,**kw):calls.append(kw);return Response()
    monkeypatch.setattr(auto_relevance.httpx,'post',post)
    return calls


def test_sentiment_first_can_start_relevance_without_unapproved_write(monkeypatch):
    from app import openai_triage
    db=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='UNASSESSED',sentiment='POSITIVE',
            sentiment_model='earlier-sentiment'))
        db.commit()
        monkeypatch.setattr(openai_triage,'openai_triage_configured',lambda:True)
        assert campaign_action(db,officer(),'campaignSingleAssessmentPreview',
            {'result_id':'1'},'91')['estimated_ai_requests']==1
        assert db.query(AIAssessmentJob).count()==0
        with pytest.raises(ValueError,match='Explicit AI cost'):
            campaign_action(db,officer(),'campaignSingleAssessmentStart',
                {'result_id':'1'},'91')
        assert db.query(AIAssessmentJob).count()==0
        result=campaign_action(db,officer(),'campaignSingleAssessmentStart',
            {'result_id':'1','confirm_ai_cost':True},'91')
        assert result['job_queued'] and not result['paid_ai_executed']
        assert db.query(AIAssessmentJob).one().state=='PENDING'
    finally:db.close()


def test_worker_appends_version_and_preserves_sentiment_first_annotation(monkeypatch):
    from app import auto_relevance
    db=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='UNASSESSED',sentiment='POSITIVE',
            sentiment_confidence='HIGH',sentiment_model='manual-original',
            sentiment_explanation='Clearly positive source'))
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'))
        db.commit()
        calls=fake_ai(monkeypatch,db)
        auto_relevance._assess_pending_campaign_locked(91,requested_limit=1,target_result_id=1)
        rows=db.query(EvidenceAssessment).order_by(EvidenceAssessment.assessment_version).all()
        assert [x.assessment_version for x in rows]==[1,2]
        assert rows[-1].relevance_label=='RELEVANT'
        assert rows[-1].sentiment=='POSITIVE'
        assert rows[-1].sentiment_model=='manual-original'
        assert rows[-1].sentiment_confidence=='HIGH'
        assert db.query(AIAssessmentJob).one().state=='COMPLETED'
        assert len(calls)==1
    finally:db.close()


def test_invalid_sentiment_is_unclassified_and_not_inadvertently_rebilled(monkeypatch):
    from app import auto_relevance
    db=fixture()
    try:
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'));db.commit()
        calls=fake_ai(monkeypatch,db,sentiment='INVALID')
        auto_relevance._assess_pending_campaign_locked(91,requested_limit=1,target_result_id=1)
        row=db.query(EvidenceAssessment).one()
        assert row.relevance_label=='RELEVANT'
        assert row.sentiment=='UNCLASSIFIED'
        assert row.sentiment_model=='gpt-4o-mini'
        assert campaign_action(db,officer(),'campaignSentimentBatchPreview',{},'91')['estimated_ai_calls']==0
        assert len(calls)==1
    finally:db.close()


def test_relevance_backlog_counts_sentiment_only_and_uses_bounded_batch(monkeypatch):
    db=fixture(21)
    try:
        monkeypatch.setenv('BAWASLU_AI_ASSESSMENTS_PER_RUN','20')
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='UNASSESSED',sentiment='NEUTRAL',sentiment_model='test'))
        db.commit()
        p=campaign_action(db,officer(),'campaignAssessmentBacklogPreview',{},'91')
        assert p['unassessed']==21 and p['batch_limit']==10
        assert not p['paid_ai_executed']
        assert campaign_action(db,officer(),'campaignAssessmentBacklogPreview',
            {'sample_limit':20},'91')['batch_limit']==20
        with pytest.raises(ValueError,match='between 1 and 20'):
            campaign_action(db,officer(),'campaignAssessmentBacklogPreview',
                {'sample_limit':21},'91')
    finally:db.close()


def test_human_relevance_correction_retains_sentiment_explanation_and_model():
    db=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT',sentiment='NEUTRAL',
            sentiment_confidence='HIGH',sentiment_model='saved-model',
            sentiment_explanation='Factual source'))
        db.commit()
        result=campaign_action(db,officer(),'campaignAssessmentCorrection',
            {'result_id':'1','decision':'UNCERTAIN',
             'rationale':'Not enough context for a definitive relevance label.'},'91')
        assert result['saved'] is True
        row=db.query(EvidenceAssessment).order_by(EvidenceAssessment.assessment_version.desc()).first()
        assert (row.sentiment,row.sentiment_confidence,row.sentiment_model,
                row.sentiment_explanation)==('NEUTRAL','HIGH','saved-model','Factual source')
    finally:db.close()


def test_keyword_leads_do_not_trigger_violation_or_attention_in_inbox_watchlist():
    db=fixture()
    try:
        db.add(IssueCategory(id=7,name='Unverified issue',active=True))
        db.add(IssueCategoryPhrase(category_id=7,phrase='politik uang',
            normalized_phrase='politik uang',active=True))
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT',potential_issue_signals_json='[]'))
        db.commit()
        data=campaign_action(db,officer(),'campaignIntelligenceInbox',{},None)
        row=next(x for x in data['findings'] if x['id']=='1')
        assert row['potential_issues']==[]
        assert len(row['issue_review_leads'])>0
        assert row['is_flagged'] is False
        assert data['violation_diagnostics']['keyword_review_lead_posts']==1
        assert data['classification_processing']['intelligence_players']['Needs Attention']['count']==0
        post=db.get(SocialListeningResult,1)
        shared=saved_classifications_for_posts(db,officer(),[post])[1][0]
        assert shared['signal_source']=='KEYWORD_REVIEW_LEAD'
        assert shared['is_flagged'] is False
    finally:db.close()


def test_officer_dismissal_stays_reviewable_after_sentiment_appends_version():
    db=fixture()
    try:
        first=EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT')
        second=EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=2,
            relevance_label='RELEVANT',sentiment='NEGATIVE',sentiment_model='test')
        db.add_all([first,second]);db.flush()
        db.add(EvidenceReview(assessment_id=first.id,reviewer_id='11',
            decision='FURTHER_INVESTIGATION',
            rationale='[Manual flag: Unverified] Initial source concern'))
        db.commit()
        result=campaign_action(db,officer(),'campaignFlagReview',
            {'result_id':'1','assessment_version':2,'decision':'FLAG_DISMISSED',
             'rationale':'No actionable allegation after human source verification.'},'91')
        assert result['saved'] is True
        found=campaign_action(db,officer(),'campaignIntelligenceInbox',{},None)['findings'][0]
        assert found['flag_review_status']=='FLAG_DISMISSED'
        assert found['is_flagged'] is False
    finally:db.close()


def test_blank_text_skipped_before_any_paid_sentiment_request(monkeypatch):
    from app import openai_triage
    db=fixture()
    try:
        db.get(SocialListeningResult,1).text_content=''
        db.commit()
        assert campaign_action(db,officer(),'campaignSentimentBatchPreview',{},'91')['estimated_ai_calls']==0
        monkeypatch.setattr(openai_triage,'openai_triage_configured',lambda:True)
        with pytest.raises(ValueError,match='Source text is missing'):
            _classify_campaign_sentiment(db,officer(),
                db.get(MonitoringCampaign,91),{'result_id':'1','confirm_ai_cost':True})
    finally:db.close()


def test_ui_distinguishes_keyword_cues_from_saved_ai_issue_signals():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]/'frontend/src'
    assert 'Keyword review cues (not violation flags)' in (
        root/'pages/Inbox.jsx').read_text(encoding='utf-8')
    assert 'Saved sentiment:' in (root/'pages/Inbox.jsx').read_text(encoding='utf-8')
    assert 'assessment.sentiment_confidence' in (
        root/'pages/WatchlistPosts.jsx').read_text(encoding='utf-8')
