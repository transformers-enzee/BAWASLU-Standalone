"""Four-item batch: source-grounded topics, player claims, reuse, diagnostic safeguards."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment
from app.access import default_permissions
from app.campaigns import campaign_action
from app.classification_enrichment import normalize_topics, normalize_concerns, normalize_attention

BODY='Warga mempertanyakan daftar pemilih dalam pemilu dan meminta penjelasan.'
QUOTE='Warga mempertanyakan daftar pemilih dalam pemilu'

def officer():
    return {'id':'11','status':'Active','role':'National Administrator',
            'geographic_scope':'Nationwide',
            'permissions':default_permissions('National Administrator')}

def db_setup():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    db.add(MonitoringCampaign(id=91,name='QA',created_by='11',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',
        text_content=BODY,author_name='Reporter',canonical_url='https://example.test/1'))
    db.add(CampaignEvidence(campaign_id=91,result_id=1))
    db.commit()
    return db

def test_topic_labels_are_saved_and_do_not_claim_keyword_hints_as_model_output():
    db=db_setup()
    try:
        snap=campaign_action(db,officer(),'campaignAcceptanceSnapshot',{},'91')
        item={r['number']:r for r in snap['items']}
        assert item[7]['production_state']=='NEEDS_SAVED_AI_TOPICS'
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,
            assessment_version=1,relevance_label='RELEVANT',
            topic_labels_json='["Electoral Operations"]',sentiment='NEUTRAL'))
        db.commit()
        snap=campaign_action(db,officer(),'campaignAcceptanceSnapshot',{},'91')
        assert {r['number']:r for r in snap['items']}[7]['production_state']=='SAVED_AI_TOPIC_EVIDENCE'
        assert normalize_topics(['Electoral Operations'],BODY,'RELEVANT')==['Electoral Operations']
        assert normalize_topics(['Electoral Operations'],BODY,'IRRELEVANT')==[]
    finally:db.close()

def test_player_concerns_require_real_quotes_and_no_assumed_guilt():
    raw=[{'evidence_quote':QUOTE,'concern':'Voter-list questions'}]
    concerns=normalize_concerns(raw,BODY,'RELEVANT')
    assert len(concerns)==1 and concerns[0]['legal_violation_confirmed'] is False
    assert normalize_concerns(raw,'Pemilu lancar','RELEVANT')==[]
    assert normalize_attention({'evidence_quote':QUOTE,'seriousness':'MEDIUM',
             'urgency':'LOW'},BODY,[],concerns)['actionability']=='HUMAN_TRIAGE_ONLY'

def test_cross_module_inbox_reuses_latest_saved_assessment_without_new_ai():
    db=db_setup()
    try:
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,
            assessment_version=1,relevance_label='RELEVANT',
            sentiment='NEGATIVE',topic_labels_json='["Electoral Operations"]'))
        db.commit()
        result=campaign_action(db,officer(),'campaignIntelligenceInbox',
                               {'campaign_id':'91'},None)
        found=[x for x in result['findings'] if str(x['id'])=='1']
        assert len(found)==1
        assert found[0]['sentiment']=='NEGATIVE'
        assert found[0]['topic_labels']==['Electoral Operations']
    finally:db.close()

def test_processing_diagnostics_do_not_infer_zero_spend():
    db=db_setup()
    try:
        data=campaign_action(db,officer(),'campaignUsageDiagnostics',{},'91')
        assert data['paid_provider_called'] is False
        assert data['ai_usage']['actual_total_usd'] is None
        assert data['posts_missing_assessment']==1
    finally:db.close()
