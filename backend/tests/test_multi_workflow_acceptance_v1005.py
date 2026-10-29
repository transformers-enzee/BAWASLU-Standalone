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

def test_source_location_cue_distinguishes_incident_from_profile_location():
 from app.processing_hints import incident_location_cues
 assert incident_location_cues('Dugaan pelanggaran di Jawa Timur diselidiki Bawaslu')==['Jawa Timur']
 assert incident_location_cues('Akun dari Jawa Timur membahas pemilu')==[]

def test_attention_requires_evidence_not_keyword_alarm():
 from app.processing_hints import attention_evidence_readiness
 evidence='Warga melaporkan dugaan pelanggaran di Jawa Timur.'
 base={'text_content':evidence,'potential_issues':[]}
 assert attention_evidence_readiness(base)['supported_quote_count']==0
 with_quote={**base,'potential_issues':[{'evidence_quote':'dugaan pelanggaran di Jawa Timur'}]}
 checked=attention_evidence_readiness(with_quote)
 assert checked['supported_quote_count']==1
 assert checked['actionability']=='HUMAN_TRIAGE_ONLY'
 assert checked['legal_violation_confirmed'] is False

def test_emerging_narrative_requires_independent_authors_and_dates():
 from app.processing_hints import emerging_narrative_candidates
 from datetime import date,timedelta
 def row(n,author,days,text='Warga mempertanyakan daftar pemilih nomor '+str(1)):
  return {'id':str(n),'campaign_id':'91','relevance_label':'RELEVANT',
    'author_name':author,'canonical_url':'https://example.test/narrative/'+str(n),
    'text_content':text+str(n),'published_at':str(date(2026,10,1)+timedelta(days=days))}
 distinct=[row(1,'a',0),row(2,'b',1),row(3,'c',2)]
 found=emerging_narrative_candidates(distinct)
 assert len(found)==1
 assert found[0]['status']=='RECURRING_DISCUSSION_CANDIDATE'
 assert found[0]['incident_verified'] is False
 assert found[0]['distinct_authors']==3
 same_author=[{**x,'author_name':'same'} for x in distinct]
 assert emerging_narrative_candidates(same_author)==[]
 outside=[row(1,'a',0),row(2,'b',120),row(3,'c',250)]
 assert emerging_narrative_candidates(outside)==[]

def test_duplicate_text_does_not_prove_incident_or_merge_campaigns():
 from app.processing_hints import exact_source_groups
 rows=[{'id':str(i),'campaign_id':c,'text_content':'identical source wording'}
       for i,c in [(1,'91'),(2,'91'),(3,'92')]]
 groups=exact_source_groups(rows)
 assert len(groups)==1
 assert groups[0]['campaign_id']=='91'
 assert groups[0]['post_ids']==['1','2']
 assert groups[0]['incident_verified'] is False
