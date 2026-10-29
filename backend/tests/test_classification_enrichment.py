"""Zero-paid-call QA: topics, player summaries, attention, failure/usage diagnostics."""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
    EvidenceAssessment,AIAssessmentJob,AssessmentAIUsage)
from app.access import default_permissions
from app.classification_enrichment import (
    normalize_topics,normalize_concerns,normalize_attention,normalize_summaries,
    token_usage)
from app.processing_hints import summarize_scoped_findings
from app.campaigns import campaign_action
from app.assessment_usage import campaign_usage_diagnostics
from app.saved_assessment_views import saved_classifications_for_posts


SOURCE='Warga mempertanyakan daftar pemilih dalam pemilu dan meminta penjelasan.'
QUOTE='Warga mempertanyakan daftar pemilih dalam pemilu'


def user(role='National Administrator'):
    return {'id':'11','name':'Test Officer','role':role,'status':'Active',
            'geographic_scope':'Nationwide','permissions':default_permissions(role)}


def fixture():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    db.add(MonitoringCampaign(id=91,name='Election oversight',
        created_by='11',primary_keywords_json='["pemilu"]',
        secondary_keywords_json='[]',excluded_keywords_json='[]'))
    db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
        author_name='Resident',canonical_url='https://example.test/post/1',
        text_content=SOURCE,published_at='2026-10-29T00:00:00Z'))
    db.add(CampaignEvidence(campaign_id=91,result_id=1))
    db.commit()
    return db


def test_topics_do_not_infer_labels_from_greetings_or_irrelevance():
    assert normalize_topics(['Electoral Operations'],'Selamat Hari Pemilu','RELEVANT')==[]
    assert normalize_topics(['Electoral Operations'],'Pemilu berlangsung','IRRELEVANT')==[]
    assert normalize_topics(['Electoral Operations','BAWASLU Reputation','Invalid'],
        'Kritik terhadap BAWASLU dan pemilu','RELEVANT')==[
        'BAWASLU Reputation','Electoral Operations']


def test_public_concerns_require_source_quote_and_complaint_cue():
    raw=[{'evidence_quote':QUOTE,'concern':'Residents question voter lists'}]
    found=normalize_concerns(raw,SOURCE,'RELEVANT')
    assert len(found)==1 and found[0]['legal_violation_confirmed'] is False
    assert normalize_concerns(raw,'Pemilu berlangsung lancar','RELEVANT')==[]
    assert normalize_concerns(
        [{'evidence_quote':'Invented 9999 source quotation','concern':'False'}],
        SOURCE,'RELEVANT')==[]
    assert normalize_concerns(raw,SOURCE,'IRRELEVANT')==[]


def test_needs_attention_safeguards_and_evidence_quote_validation():
    concern=normalize_concerns(
        [{'evidence_quote':QUOTE,'concern':'Voter list concern'}],SOURCE,'RELEVANT')
    proposal={'seriousness':'HIGH','urgency':'HIGH','evidence_quote':QUOTE}
    item=normalize_attention(proposal,SOURCE,[],concern)
    assert item['seriousness']=='HIGH' and item['urgency']=='HIGH'
    assert item['actionability']=='HUMAN_TRIAGE_ONLY'
    assert item['legal_violation_confirmed'] is False
    assert normalize_attention(proposal,SOURCE,[],{})=={}
    assert normalize_attention({**proposal,'evidence_quote':'fabricated quotation here'},
                               SOURCE,[],concern)=={}


def test_ai_summaries_are_source_quoted_drafts_and_reject_guilt_claims():
    result=normalize_summaries([
        {'player':'Public Concerns','source_quote':QUOTE,
         'summary':'Residents have raised questions about the voter register.'},
        {'player':'Potential Violations','source_quote':'fabricated evidence',
         'summary':'This event is definitely illegal.'},
        {'player':'Reviewed History','source_quote':QUOTE,
         'summary':'Human decisions cannot be generated from a post.'},
        {'player':'Public Concerns','source_quote':QUOTE,
         'summary':'This actor is proven guilty of wrongdoing.'},
    ],SOURCE,'RELEVANT')
    assert len(result)==1
    assert result[0]['status']=='AI_DRAFT_REQUIRES_HUMAN_REVIEW'
    assert result[0]['legal_violation_confirmed'] is False


def test_provider_usage_is_never_equated_to_zero_dollar_cost():
    tokens=token_usage({'prompt_tokens':210,'completion_tokens':30})
    assert tokens['input_tokens']==210 and tokens['output_tokens']==30
    assert tokens['usage_reported'] is True
    assert tokens['cost_usd']==''
    assert tokens['cost_status']=='NOT_REPORTED_BY_PROVIDER'
    assert token_usage(None)['usage_reported'] is False


def fake_worker(monkeypatch,db):
    from app import auto_relevance
    monkeypatch.setenv('OPENAI_API_KEY','fake-key-never-call-real-provider')
    monkeypatch.setenv('BAWASLU_AI_ASSESSMENTS_PER_RUN','10')
    monkeypatch.setattr(auto_relevance,'SessionLocal',lambda:Session(db.get_bind()))
    monkeypatch.setattr(auto_relevance,'reserve_automatic_ai_request',lambda *_:True)
    calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):
            output={'relevance_label':'RELEVANT','confidence':'MEDIUM',
                'explanation':'Election administration discussion',
                'sentiment':'NEGATIVE','sentiment_confidence':'MEDIUM',
                'sentiment_explanation':'The writer questions officials.',
                'gate_answers':[],'candidates':[],'locations':[],
                'issue_category_ids':[],'potential_violation_signals':[],
                'reported_incident_signals':[],
                'topics':['Electoral Operations'],
                'public_concern_signals':[{'evidence_quote':QUOTE,
                                          'concern':'Questions about voter registration'}],
                'attention':{'seriousness':'MEDIUM','urgency':'LOW',
                             'evidence_quote':QUOTE},
                'player_summaries':[{'player':'Public Concerns',
                    'source_quote':QUOTE,
                    'summary':'Residents seek clarification about voter registration.'}]}
            return {'choices':[{'message':{'content':json.dumps(output)}}],
                'usage':{'prompt_tokens':210,'completion_tokens':80}}
    def post(*args,**kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr(auto_relevance.httpx,'post',post)
    return calls


def test_existing_ai_worker_persists_player_results_and_usage_once(monkeypatch):
    from app import auto_relevance
    db=fixture()
    try:
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'))
        db.commit()
        calls=fake_worker(monkeypatch,db)
        auto_relevance._assess_pending_campaign_locked(
            91,requested_limit=1,target_result_id=1)
        assessment=db.query(EvidenceAssessment).one()
        assert json.loads(assessment.topic_labels_json)==['Electoral Operations']
        assert len(json.loads(assessment.public_concern_signals_json))==1
        assert json.loads(assessment.attention_assessment_json)['urgency']=='LOW'
        assert json.loads(assessment.player_summaries_json)[0]['player']=='Public Concerns'
        usage=db.query(AssessmentAIUsage).one()
        assert usage.assessment_id==assessment.id
        assert (usage.input_tokens,usage.output_tokens)==(210,80)
        assert usage.cost_status=='NOT_REPORTED_BY_PROVIDER'
        assert len(calls)==1
    finally:db.close()


def test_intelligence_player_uses_saved_evidence_not_fake_verified_violation(monkeypatch):
    from app import auto_relevance
    db=fixture()
    try:
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'))
        db.commit()
        fake_worker(monkeypatch,db)
        auto_relevance._assess_pending_campaign_locked(
            91,requested_limit=1,target_result_id=1)
        inbox=campaign_action(db,user(),'campaignIntelligenceInbox',
                              {'campaign_id':'91'},None)
        item=inbox['findings'][0]
        assert item['topic_labels']==['Electoral Operations']
        assert len(item['public_concern_signals'])==1
        assert item['attention_assessment']['seriousness']=='MEDIUM'
        assert len(item['player_summaries'])==1
        players=inbox['classification_processing']['intelligence_players']
        assert players['Public Concerns']['count']==1
        assert players['Potential Violations']['count']==0
        assert players['Needs Attention']['count']==0
        shared=saved_classifications_for_posts(
            db,user(),[db.get(SocialListeningResult,1)])[1][0]
        assert shared['topic_labels']==['Electoral Operations']
        assert len(shared['player_summary_drafts'])==1
    finally:db.close()


def test_human_correction_retains_topics_and_source_based_summaries(monkeypatch):
    from app import auto_relevance
    db=fixture()
    try:
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'))
        db.commit()
        fake_worker(monkeypatch,db)
        auto_relevance._assess_pending_campaign_locked(
            91,requested_limit=1,target_result_id=1)
        campaign_action(db,user(),'campaignAssessmentCorrection',{'result_id':'1',
            'decision':'UNCERTAIN',
            'rationale':'The evidence does not establish a reliable event connection.'},'91')
        versions=db.query(EvidenceAssessment).order_by(
            EvidenceAssessment.assessment_version).all()
        assert len(versions)==2
        assert versions[-1].topic_labels_json==versions[0].topic_labels_json
        assert versions[-1].public_concern_signals_json==versions[0].public_concern_signals_json
        assert versions[-1].attention_assessment_json==versions[0].attention_assessment_json
        assert versions[-1].player_summaries_json==versions[0].player_summaries_json
    finally:db.close()


def test_usage_and_failure_diagnostics_do_not_bill_or_invent_costs(monkeypatch):
    from app import auto_relevance
    db=fixture()
    try:
        db.add(AIAssessmentJob(campaign_id=91,result_id=1,state='PENDING'))
        db.commit()
        fake_worker(monkeypatch,db)
        auto_relevance._assess_pending_campaign_locked(
            91,requested_limit=1,target_result_id=1)
        data=campaign_usage_diagnostics(db,user(),'91')
        assert data['authorized_source_posts']==1
        assert data['ai_usage']['input_tokens_reported']==210
        assert data['ai_usage']['output_tokens_reported']==80
        assert data['ai_usage']['actual_total_usd'] is None
        assert data['ai_usage']['cost_status']=='NOT_AVAILABLE_FROM_PROVIDER'
        assert data['paid_provider_called'] is False
        assert data['job_states']['COMPLETED']==1
    finally:db.close()


def test_readonly_dispatcher_routes_new_group_and_usage_actions():
    from app.socialcrawl import social_listening_action
    db=fixture()
    try:
        assert social_listening_action(db,user(),'campaignFindingGroupsPreview',
            {},'91')['paid_provider_called'] is False
        usage=social_listening_action(db,user(),'campaignUsageDiagnostics',{},'91')
        assert usage['authorized_source_posts']==1
        assert usage['paid_provider_called'] is False
    finally:db.close()


def test_frontend_displays_player_drafts_and_usage_with_uncertainty():
    from pathlib import Path
    src=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx'
         ).read_text(encoding='utf-8')
    assert 'AI topic classification:' in src
    assert 'Source-referenced AI summary drafts' in src
    assert 'Load AI usage and failure diagnostics (free)' in src
    assert 'Human verification required' in src
