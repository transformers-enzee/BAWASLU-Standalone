"""Workflow acceptance: one mocked provider response, real persisted outputs, no paid calls."""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment
from app.access import default_permissions
from app.campaigns import campaign_action
from app.saved_assessment_views import saved_classifications_for_posts
from app.processing_hints import summarize_scoped_findings

SOURCE='Ratusan massa meminta Bawaslu bertanggung jawab atas buruknya kualitas Pemilu 2024.'
QUOTE='Ratusan massa meminta Bawaslu bertanggung jawab atas buruknya kualitas Pemilu 2024.'

def profile():
 return {'id':'1','role':'National Administrator','status':'Active','geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}

def session():
 db=Session(create_engine('sqlite:///:memory:'))
 Base.metadata.create_all(db.get_bind())
 db.add(MonitoringCampaign(id=91,name='Election QA',created_by='1',primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
 db.add(SocialListeningResult(id=225,run_id=1,platform='instagram',text_content=SOURCE,canonical_url='https://example.test/225',author_name='Reporter',published_at='2024-02-19T00:00:00Z'))
 db.add(CampaignEvidence(campaign_id=91,result_id=225))
 db.add(EvidenceAssessment(campaign_id=91,result_id=225,assessment_version=1,model_version='mocked-provider',relevance_label='RELEVANT',sentiment='NEGATIVE',topic_labels_json='["BAWASLU Reputation"]',public_concern_signals_json=json.dumps([{'evidence_quote':QUOTE,'concern':'Public accountability demand','status':'AI_CONCERN_SIGNAL_UNVERIFIED','legal_violation_confirmed':False}]),potential_issue_signals_json='[]'))
 db.commit()
 return db

def test_saved_assessment_reused_in_inbox_and_canonical_shared_view():
 db=session()
 try:
  inbox=campaign_action(db,profile(),'campaignIntelligenceInbox',{'campaign_id':'91'})
  found=[row for row in inbox['findings'] if str(row['id'])=='225']
  assert len(found)==1
  row=found[0]
  shared=saved_classifications_for_posts(db,profile(),[db.get(SocialListeningResult,225)])[225]
  assert len(shared)==1
  same=shared[0]
  assert same['canonical_source_id']=='social:225'
  for key in ('assessment_version','relevance_label','sentiment','topic_labels','public_concern_signals'):
   assert row[key]==same[key],(key,row[key],same[key])
  assert same['human_validation_required'] is True
  assert inbox['classification_processing']['intelligence_players']['Public Concerns']['count']==1
 finally:db.close()

def test_workflow_does_not_invent_violation_or_narrative():
 db=session()
 try:
  result=campaign_action(db,profile(),'campaignIntelligenceInbox',{'campaign_id':'91'})
  players=result['classification_processing']['intelligence_players']
  assert players['Potential Violations']['count']==0
  assert players['Emerging Narratives']['count']==0
  assert result['classification_processing']['narratives_verified']==0
 finally:db.close()

def test_unassessed_source_is_not_claimed_to_be_processed():
 db=session()
 try:
  db.add(SocialListeningResult(id=226,run_id=1,platform='instagram',text_content='Other post',canonical_url='https://example.test/226'))
  db.add(CampaignEvidence(campaign_id=91,result_id=226));db.commit()
  results=saved_classifications_for_posts(db,profile(),[db.get(SocialListeningResult,226)])
  assert results[226]==[]
 finally:db.close()
