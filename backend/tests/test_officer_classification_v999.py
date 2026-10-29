import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,CampaignEvidence,SocialListeningResult,EvidenceAssessment,EvidenceReview
from app.access import default_permissions
from app.officer_classification_correction import correct_classification

BODY='Ratusan massa meminta Badan Pengawas Pemilihan Umum (Bawaslu) RI bertanggung jawab atas buruknya kualitas Pemilu 2024.'
QUOTE='Ratusan massa meminta Badan Pengawas Pemilihan Umum (Bawaslu) RI bertanggung jawab'
def setup():
 db=Session(create_engine('sqlite:///:memory:'))
 Base.metadata.create_all(db.get_bind())
 db.add(MonitoringCampaign(id=9,name='Test',created_by='1',primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
 db.add(SocialListeningResult(id=225,run_id=1,platform='instagram',text_content=BODY))
 db.add(CampaignEvidence(campaign_id=9,result_id=225))
 db.add(EvidenceAssessment(campaign_id=9,result_id=225,assessment_version=3,relevance_label='RELEVANT',sentiment='NEGATIVE',topic_labels_json='["BAWASLU Reputation"]',potential_issue_signals_json='[{"evidence_quote":"unaltered"}]'))
 db.commit()
 return db
def officer():
 return {'id':'1','role':'National Administrator','status':'Active','geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}
def test_source_quoted_concern_preserves_original_and_issue():
 db=setup()
 try:
  result=correct_classification(db,officer(),9,{'result_id':225,'expected_version':3,'correction_type':'PUBLIC_CONCERN','source_quote':QUOTE,'concern':'People demanded accountability for poor election quality','rationale':'The quoted passage explicitly requests institutional accountability.'})
  assert result['assessment_version']==4 and not result['paid_provider_called']
  entries=db.query(EvidenceAssessment).order_by(EvidenceAssessment.assessment_version).all()
  assert len(entries)==2
  assert entries[0].public_concern_signals_json in (None,'[]')
  assert entries[1].potential_issue_signals_json==entries[0].potential_issue_signals_json
  assert json.loads(entries[1].public_concern_signals_json)[0]['status']=='HUMAN_CONCERN_REVIEWED'
  assert db.query(EvidenceReview).count()==1
 finally:db.close()
def test_topic_removal_and_stale_version_rejection():
 db=setup()
 try:
  data={'result_id':225,'expected_version':3,'correction_type':'TOPICS','topics':[],
        'rationale':'The source does not establish the selected topic.'}
  assert correct_classification(db,officer(),9,data)['assessment_version']==4
  with pytest.raises(ValueError,match='changed'):
   correct_classification(db,officer(),9,data)
 finally:db.close()
def test_viewer_cannot_correct():
 db=setup()
 try:
  with pytest.raises(PermissionError):
   correct_classification(db,{'id':'8','role':'Viewer','status':'Active','permissions':default_permissions('Viewer')},9,
       {'result_id':225,'expected_version':3,'correction_type':'TOPICS','topics':[],'rationale':'Unsupported original topic label'})
 finally:db.close()
