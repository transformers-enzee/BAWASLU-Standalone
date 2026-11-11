"""End-to-end saved sentiment QA, with provider requests fully mocked."""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
                        EvidenceAssessment,AIAssessmentJob)
from app.access import default_permissions
from app.sentiment_processing import normalize_sentiment_output,sentiment_is_assessed
from app.campaigns import campaign_action,_classify_campaign_sentiment


def principal():
    return {'id':'11','name':'Test Admin','role':'National Administrator',
            'geographic_scope':'Nationwide','status':'Active',
            'permissions':default_permissions('National Administrator')}


def db_with_posts(count=2):
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    campaign=MonitoringCampaign(id=91,name='Election oversight',created_by='11',
        primary_keywords_json='["pemilu"]',secondary_keywords_json='[]',
        excluded_keywords_json='[]')
    db.add(campaign)
    for n in range(1,count+1):
        db.add(SocialListeningResult(id=n,run_id=1,platform='instagram',
            author_name='Reporter',text_content='Warga mengkritik layanan pemilu '+str(n),
            published_at='2026-10-29T01:00:00Z',engagement_json='{}'))
        db.add(CampaignEvidence(campaign_id=91,result_id=n,matched_fields_json='{}'))
    db.commit()
    return db,campaign


def test_sentiment_labels_are_normalized_not_hallucinated():
    item=normalize_sentiment_output({'sentiment':'negative','sentiment_confidence':'MEDIUM',
                                   'sentiment_explanation':'Author explicitly criticizes the service.'})
    assert item['sentiment']=='NEGATIVE' and item['sentiment_confidence']=='MEDIUM'
    assert normalize_sentiment_output({'sentiment':'party A'})['sentiment']=='UNCLASSIFIED'
    assert normalize_sentiment_output(None)['valid'] is False


def test_batch_default_ten_max_twenty_and_no_paid_preview():
    db,_=db_with_posts(21)
    try:
        default=campaign_action(db,principal(),'campaignSentimentBatchPreview',{},'91')
        assert len(default['selected_ids'])==10
        assert default['paid_provider_called'] is False
        larger=campaign_action(db,principal(),'campaignSentimentBatchPreview',
                               {'sample_limit':20},'91')
        assert len(larger['selected_ids'])==20
        with pytest.raises(ValueError,match='between 1 and 20'):
            campaign_action(db,principal(),'campaignSentimentBatchPreview',
                            {'sample_limit':21},'91')
    finally:db.close()


def test_dashboard_counts_saved_labels_and_recomputes_on_new_assessment():
    db,_=db_with_posts(2)
    try:
        before=campaign_action(db,principal(),'campaignDashboard',{},'91')
        assert before['sentiment']['Unclassified']==0
        assert before['sentiment_pending_count']==2
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            sentiment='NEGATIVE',sentiment_model='test',
            relevance_label='RELEVANT'))
        db.commit()
        after=campaign_action(db,principal(),'campaignDashboard',{},'91')
        assert after['sentiment']['Negative']==1
        assert after['sentiment']['Unclassified']==0
        assert after['sentiment_pending_count']==1
        assert after['sentiment_classified_count']==1
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=2,
            sentiment='POSITIVE',sentiment_model='test',relevance_label='RELEVANT'))
        db.commit()
        updated=campaign_action(db,principal(),'campaignDashboard',{},'91')
        assert updated['sentiment']['Positive']==1 and updated['sentiment']['Negative']==0
    finally:db.close()


def test_worker_persists_sentiment_with_relevance_in_one_request(monkeypatch):
    from app import auto_relevance
    db,_=db_with_posts(1)
    try:
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'));db.commit()
        monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
        monkeypatch.setenv('BAWASLU_AI_ASSESSMENTS_PER_RUN','10')
        monkeypatch.setattr(auto_relevance,'SessionLocal',lambda:Session(db.get_bind()))
        monkeypatch.setattr(auto_relevance,'reserve_automatic_ai_request',lambda *_:True)
        calls=[]
        class Response:
            def raise_for_status(self):pass
            def json(self):return {'choices':[{'message':{'content':json.dumps({
                'relevance_label':'RELEVANT','confidence':'MEDIUM',
                'explanation':'Discusses election operations',
                'sentiment':'NEGATIVE','sentiment_confidence':'HIGH',
                'sentiment_explanation':'Explicit dissatisfaction',
                'candidates':[],'locations':[],'gate_answers':[],
                'issue_category_ids':[],'reported_incident_signals':[],
                'potential_violation_signals':[]})}}]}
        def fake_post(*a,**kw):calls.append(kw);return Response()
        monkeypatch.setattr(auto_relevance.httpx,'post',fake_post)
        auto_relevance._assess_pending_campaign_locked(91,requested_limit=1,target_result_id=1)
        saved=db.query(EvidenceAssessment).filter_by(campaign_id=91,result_id=1).one()
        assert saved.relevance_label=='RELEVANT'
        assert saved.sentiment=='NEGATIVE' and saved.sentiment_confidence=='HIGH'
        assert len(calls)==1
    finally:db.close()


def test_explicit_sentiment_action_preserves_existing_relevance_and_is_cached(monkeypatch):
    import httpx
    db,c=db_with_posts(1)
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT',relevance_confidence='HIGH',
            explanation='Existing relevance reason'))
        db.commit()
        monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
        calls=[]
        class Response:
            def raise_for_status(self):pass
            def json(self):return {'model':'mock','output_text':json.dumps({
                'sentiment':'NEUTRAL','confidence':'HIGH','explanation':'Factual report.'})}
        class Client:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def post(self,*args,**kwargs):calls.append(1);return Response()
        monkeypatch.setattr(httpx,'Client',Client)
        out=_classify_campaign_sentiment(db,principal(),c,{'result_id':'1','confirm_ai_cost':True})
        assert out['sentiment']=='Neutral' and out['confidence']=='HIGH'
        latest=db.query(EvidenceAssessment).filter_by(campaign_id=91,result_id=1).order_by(
            EvidenceAssessment.assessment_version.desc()).first()
        assert latest.assessment_version==2
        assert latest.relevance_label=='RELEVANT'
        assert latest.relevance_confidence=='HIGH'
        assert latest.explanation=='Existing relevance reason'
        assert latest.sentiment_explanation=='Factual report.'
        cached=_classify_campaign_sentiment(db,principal(),c,
            {'result_id':'1','confirm_ai_cost':True})
        assert cached['cached'] is True and not cached['paid_provider_called']
        assert len(calls)==1
    finally:db.close()


def test_uncertain_result_counts_as_assessed_to_prevent_rebilling():
    db,_=db_with_posts(1)
    try:
        assessment=EvidenceAssessment(campaign_id=91,result_id=1,
            relevance_label='RELEVANT',sentiment='UNCLASSIFIED',
            sentiment_model='model-that-assessed')
        db.add(assessment);db.commit()
        assert sentiment_is_assessed(assessment)
        # A completed but source-uncertain assessment remains genuinely Unclassified.
        dashboard=campaign_action(db,principal(),'campaignDashboard',{},'91')
        assert dashboard['sentiment']['Unclassified']==1
        assert dashboard['sentiment_pending_count']==0
        assert campaign_action(db,principal(),'campaignSentimentBatchPreview',{},'91')['estimated_ai_calls']==0
    finally:db.close()


def test_campaign_ui_refresh_and_cost_confirmation_are_explicit():
    from pathlib import Path
    file=Path(__file__).resolve().parents[2]/'frontend/src/components/intel/CampaignPanel.jsx'
    source=file.read_text(encoding='utf-8')
    # The old Overview controls were intentionally removed in v125.5.
    # Preserve checks for the underlying paid-AI confirmation and data refresh.
    assert 'Refresh saved sentiment (free)' not in source
    # The hidden legacy Captured Posts section retains its batch controls for future use.
    assert 'Sentiment batch size' in source
    assert 'confirm_ai_cost:true' in source
    assert 'setDashboard(d.data);setEvidence(e.data.evidence||[]);' in source


def test_explicit_uncertain_ai_sentiment_is_never_relabelled_neutral(monkeypatch):
    import httpx
    db,c=db_with_posts(1)
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT',explanation='Preserved relevance'))
        db.commit()
        monkeypatch.setenv('OPENAI_API_KEY','test-key-not-real')
        class Response:
            def raise_for_status(self):pass
            def json(self):return {'model':'mock','output_text':json.dumps({
                'sentiment':'UNCLASSIFIED','confidence':'HIGH',
                'explanation':'The source does not establish a clear emotional tone.'})}
        class Client:
            def __init__(self,*a,**kw):pass
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def post(self,*a,**kw):return Response()
        monkeypatch.setattr(httpx,'Client',Client)
        result=_classify_campaign_sentiment(db,principal(),c,
            {'result_id':'1','confirm_ai_cost':True})
        assert result['sentiment']=='Unclassified'
        assert result['confidence']=='LOW'
        record=db.query(EvidenceAssessment).filter_by(campaign_id=91,result_id=1).order_by(
            EvidenceAssessment.assessment_version.desc()).first()
        assert record.sentiment=='UNCLASSIFIED' and record.sentiment_confidence=='LOW'
        assert record.relevance_label=='RELEVANT'
        assert record.explanation=='Preserved relevance'
    finally:db.close()


def test_legacy_prism_null_stance_is_eligible_without_changing_saved_label():
    db,c=db_with_posts(1)
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT',sentiment='UNCLASSIFIED',
            sentiment_model='socialcrawl-prism-stance',
            sentiment_explanation='Stance toward monitored campaign topic; not a general endorsement'))
        db.commit()
        stored=db.query(EvidenceAssessment).one()
        assert not sentiment_is_assessed(stored)
        preview=campaign_action(db,principal(),'campaignSentimentBatchPreview',{},'91')
        assert preview['eligible_total']==1 and preview['selected_ids']==['1']
        assert preview['paid_provider_called'] is False
        assert stored.sentiment=='UNCLASSIFIED'
    finally:db.close()


def test_human_sentiment_correction_excludes_legacy_prism_from_paid_batch_and_action():
    from app.officer_sentiment import OfficerSentimentCorrection
    db,c=db_with_posts(1)
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,
            relevance_label='RELEVANT',sentiment='UNCLASSIFIED',
            sentiment_model='socialcrawl-prism-stance'))
        db.add(OfficerSentimentCorrection(campaign_id=91,result_id=1,sentiment='NEGATIVE',
            rationale='Human assessment',actor_id=11))
        db.commit()
        preview=campaign_action(db,principal(),'campaignSentimentBatchPreview',
            {'retry_unclassified':True},'91')
        assert preview['eligible_total']==0 and preview['already_labeled']==1
        assert preview['estimated_ai_calls']==0
        # Even an explicitly confirmed request must reuse the human label.
        result=_classify_campaign_sentiment(db,principal(),c,
            {'result_id':'1','confirm_ai_cost':True,'retry_unclassified':True})
        assert result['sentiment']=='Negative' and result['cached'] is True
        assert result['paid_provider_called'] is False
        assert db.query(EvidenceAssessment).count()==1
    finally:db.close()
