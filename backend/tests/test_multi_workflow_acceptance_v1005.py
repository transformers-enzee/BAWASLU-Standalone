"""Concurrent offline acceptance gates for pending workflow checklist items."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,CampaignEvidence,SocialListeningResult,EvidenceAssessment
from app.access import default_permissions
from app.campaigns import campaign_action

def officer():
 return {'id':'1','role':'National Administrator','status':'Active','geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}
def fixture():
 db=Session(create_engine('sqlite:///:memory:'))
 Base.metadata.create_all(db.get_bind())
 db.add(MonitoringCampaign(id=91,name='Acceptance',created_by='1',primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
 for i,txt in [(1,'Pemilu di provinsi NTT dilaporkan oleh warga'),(2,'Pemilu di provinsi NTT dilaporkan oleh warga'),(3,'Warga mengeluh soal pengawasan pemilu di TPS')]:
  db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',text_content=txt,canonical_url='https://example.test/'+str(i),author_name='Reporter'))
  db.add(CampaignEvidence(campaign_id=91,result_id=i))
 db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,relevance_label='RELEVANT'))
 db.add(EvidenceAssessment(campaign_id=91,result_id=3,assessment_version=1,relevance_label='RELEVANT'))
 db.commit()
 return db

def test_duplicate_group_preview_never_creates_officer_acceptance():
 db=fixture()
 try:
  result=campaign_action(db,officer(),'campaignFindingGroupsPreview',{},'91')
  assert result['paid_provider_called'] is False
  assert result['proposal_count']>=1
  assert any(x['type']=='EXACT_DUPLICATE' for x in result['proposals'])
 finally: db.close()

def test_no_narrative_does_not_claim_valid_absence_with_unassessed_posts():
 db=fixture()
 try:
  result=campaign_action(db,officer(),'campaignFindingGroupsReadiness',{},'91')
  assert result['unassessed_posts']>=1
  assert result['zero_group_result_is_conclusive'] is False
 finally: db.close()

def test_inbox_exposes_real_source_without_inventing_ai_or_attention():
 db=fixture()
 try:
  result=campaign_action(db,officer(),'campaignIntelligenceInbox',{'campaign_id':'91'})
  assert result['classification_processing']['paid_provider_called'] is False
  assert result['classification_processing']['narratives_verified']==0
  assert result['classification_processing']['intelligence_players']['Needs Attention']['count']==0
 finally: db.close()

def test_source_jurisdiction_preview_does_not_grant_unverified_scope():
 db=fixture()
 try:
  result=campaign_action(db,officer(),'campaignJurisdictionPreview',{'result_id':'1'},'91')
  assert result['paid_provider_called'] is False
  assert result['source_post_relevance_assessed'] is True
 finally: db.close()
