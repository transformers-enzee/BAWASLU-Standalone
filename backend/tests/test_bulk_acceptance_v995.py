"""v99.5 no-credit contract: honest narrative, summary and provider-cost status."""
import hashlib
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import (MonitoringCampaign,SocialListeningResult,CampaignEvidence,
                        EvidenceAssessment,AssessmentAIUsage)
from app.access import default_permissions
from app.campaigns import campaign_action
from app.summary_readiness import validated_summary_buckets
from app.assessment_usage import campaign_usage_diagnostics
from app.classification_enrichment import normalize_summaries

BODY='Warga mempertanyakan daftar pemilih dalam pemilu dan meminta penjelasan.'
QUOTE='Warga mempertanyakan daftar pemilih dalam pemilu'

def officer():
    return {'id':'11','role':'National Administrator','status':'Active',
            'geographic_scope':'Nationwide',
            'permissions':default_permissions('National Administrator')}

def database():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=91,name='QA',created_by='11',
           primary_keywords_json='[]',secondary_keywords_json='[]',
           excluded_keywords_json='[]'))
    db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
           text_content=BODY,canonical_url='https://example.test/1',
           author_name='Reporter'))
    db.add(CampaignEvidence(campaign_id=91,result_id=1))
    db.commit()
    return db

def test_fingerprinted_pipeline_draft_is_distinct_from_chat_and_legacy():
    pipeline=normalize_summaries([{'player':'Public Concerns','summary':
             'Citizens request clarity about the voter list.','source_quote':QUOTE}],
             BODY,'RELEVANT')[0]
    digest=hashlib.sha256(BODY.encode()).hexdigest()
    assert pipeline['source_text_sha256']==digest
    development={**pipeline,'provenance':'GPT6_CHAT_GENERATED_QA_SAMPLE'}
    legacy={k:v for k,v in pipeline.items() if k not in ('provenance','source_text_sha256')}
    buckets=validated_summary_buckets({'text_content':BODY,
          'player_summaries':[pipeline,development,legacy]})
    assert [len(buckets[k]) for k in ('pipeline','development','unattributed')]==[1,1,1]
    assert validated_summary_buckets({'text_content':BODY+' extra',
            'player_summaries':[pipeline]})['pipeline']==[]

def test_development_sample_is_not_production_acceptance():
    db=database()
    try:
        draft=normalize_summaries([{'player':'Public Concerns',
               'summary':'Citizens request clarity about the voter list.',
               'source_quote':QUOTE}],BODY,'RELEVANT')[0]
        draft['provenance']='GPT6_CHAT_GENERATED_QA_SAMPLE'
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,
            assessment_version=1,relevance_label='RELEVANT',
            sentiment='NEUTRAL',player_summaries_json=json.dumps([draft])))
        db.commit()
        snap=campaign_action(db,officer(),'campaignAcceptanceSnapshot',{},'91')
        state={x['number']:x for x in snap['items']}
        assert state[12]['production_state']=='DEVELOPMENT_SAMPLES_NOT_PIPELINE_ACCEPTANCE'
        action={x['item']:x for x in snap['next_actions']}
        assert action[12]['status']=='DEVELOPMENT_SAMPLES_NOT_PIPELINE_ACCEPTANCE'
        assert snap['summary_evidence']['pipeline_posts']==0
        ready=campaign_action(db,officer(),'campaignSummaryReadiness',{},'91')
        assert ready['posts_with_pipeline_ai_drafts']==0
        assert ready['posts_needing_pipeline_ai_drafts']==1
        assert ready['suggested_small_pilot_ids']==['1']
    finally:db.close()

def test_fully_reported_cost_only_when_all_values_are_known():
    db=database()
    try:
        record=EvidenceAssessment(campaign_id=91,result_id=1,
                    assessment_version=1,relevance_label='RELEVANT')
        db.add(record);db.flush()
        usage=AssessmentAIUsage(assessment_id=record.id,campaign_id=91,
                    provider_model='offline-test',request_kind='RELEVANCE_AND_CLASSIFICATION',
                    input_tokens=11,output_tokens=7,usage_reported=True,
                    cost_usd='0.0012',cost_status='REPORTED')
        db.add(usage);db.commit()
        data=campaign_usage_diagnostics(db,officer(),'91')['ai_usage']
        assert data['actual_total_usd']=='0.0012'
        assert data['cost_status']=='COMPLETE_REPORTED'
        usage.cost_status='NOT_REPORTED_BY_PROVIDER';db.commit()
        data=campaign_usage_diagnostics(db,officer(),'91')['ai_usage']
        assert data['actual_total_usd'] is None
        assert data['request_costs_unknown']==1
    finally:db.close()

def test_usage_and_acceptance_require_intelligence_permission():
    db=database()
    try:
        denied={'id':'22','role':'Viewer','status':'Active',
                'geographic_scope':'Nationwide','permissions':{}}
        import pytest
        with pytest.raises(PermissionError):
            campaign_usage_diagnostics(db,denied,'91')
        with pytest.raises(PermissionError):
            campaign_action(db,denied,'campaignAcceptanceSnapshot',{},'91')
    finally:db.close()
