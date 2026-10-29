"""v99.3 source scope and temporal integrity; preserve real GPT-6 sample provenance."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment,CampaignFindingGroup
from app.access import default_permissions
from app.campaigns import campaign_action
from app.processing_hints import emerging_narrative_candidates
from app.summary_readiness import campaign_summary_readiness
import hashlib,json

def actor():
    return {'id':'11','role':'National Administrator','status':'Active',
            'geographic_scope':'Nationwide',
            'permissions':default_permissions('National Administrator')}

def narrative_rows(years):
    texts=[
      'Bawaslu NTT mengadakan coaching clinic pengawasan partisipatif untuk relawan.',
      'Peserta mengikuti program pendidikan pengawas partisipatif nasional.',
      'Bawaslu Sumba Timur meninjau hasil pengawasan partisipatif.',
    ]
    return [{'id':str(i+1),'campaign_id':'91','text_content':texts[i],
        'author_name':'Reporter '+str(i),'relevance_label':'RELEVANT',
        'canonical_url':'https://example.test/'+str(i),
        'published_at':years[i]} for i in range(3)]

def test_new_narrative_anchor_is_supported_by_three_current_independent_sources():
    rows=narrative_rows(['2026-10-27','2026-10-28','2026-10-29'])
    candidates=emerging_narrative_candidates(rows)
    found=next(x for x in candidates if x['anchor']=='Participatory election oversight')
    assert found['source_ids']==['1','2','3']
    assert found['time_basis']=='SOURCE_PUBLICATION_WITHIN_90_DAYS'
    assert found['incident_verified'] is False

def test_old_2025_post_cannot_qualify_as_emerging_in_2026():
    rows=narrative_rows(['2026-10-28','2025-09-03','2026-10-28'])
    assert not [x for x in emerging_narrative_candidates(rows)
                if x['anchor']=='Participatory election oversight']

def test_gpt6_development_sample_is_counted_but_not_as_pipeline_or_approval():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        text='Bawaslu Sumatra Selatan menemukan dugaan pencoblosan lebih dari sekali.'
        quote='menemukan dugaan pencoblosan lebih dari sekali'
        db.add(MonitoringCampaign(id=91,name='QA',created_by='11',
            primary_keywords_json='[]',secondary_keywords_json='[]',
            excluded_keywords_json='[]'))
        db.add(SocialListeningResult(id=1,run_id=1,platform='instagram',text_content=text))
        db.add(CampaignEvidence(campaign_id=91,result_id=1))
        draft={'player':'Potential Violations','summary':
               'Unggahan menyebut dugaan pencoblosan ganda yang belum diverifikasi.',
               'source_quote':quote,'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW',
               'provenance':'GPT6_CHAT_GENERATED_QA_SAMPLE',
               'source_text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest()}
        db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=2,
            relevance_label='RELEVANT',sentiment='NEUTRAL',
            player_summaries_json=json.dumps([draft])))
        db.commit()
        status=campaign_summary_readiness(db,actor(),'91')
        assert status['posts_with_valid_saved_ai_drafts']==1
        assert status['posts_with_development_chatgpt_samples']==1
        assert status['posts_with_pipeline_ai_drafts']==0
        assert status['human_approved_summary_count']==0
        assert status['manual_sample_is_not_pipeline_acceptance'] is True
        post=db.get(SocialListeningResult,1)
        post.text_content='Edited material replacing the prior source quote'
        db.commit()
        new_status=campaign_summary_readiness(db,actor(),'91')
        assert new_status['posts_with_valid_saved_ai_drafts']==0
    finally:db.close()

def test_automated_proposer_is_explicit_and_never_reviewed_by_default():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        item=CampaignFindingGroup(campaign_id=91,group_key='f'*64,
            group_type='EXACT_DUPLICATE',label='Repeated source',
            source_ids_json='["1","2"]',review_status='PROPOSED',
            created_by='system:chatgpt-provisional-requested')
        from app.finding_groups import serialize_group
        val=serialize_group(item)
        assert val['proposed_by_automation'] is True
        assert val['grouping_reviewed'] is False
        assert val['legal_violation_confirmed'] is False
    finally:db.close()
