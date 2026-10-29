"""The public Social Listening router must recognize the correction action."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.access import default_permissions
from app.socialcrawl import social_listening_action

def test_officer_correction_reaches_authenticated_dispatcher():
 db=Session(create_engine('sqlite:///:memory:'))
 try:
  Base.metadata.create_all(db.get_bind())
  db.add(MonitoringCampaign(id=91,name='QA',created_by='11',primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
  db.add(SocialListeningResult(id=232,run_id=1,platform='instagram',text_content='Comedy with election hashtags'))
  db.add(CampaignEvidence(campaign_id=91,result_id=232))
  db.add(EvidenceAssessment(campaign_id=91,result_id=232,assessment_version=2,relevance_label='RELEVANT',topic_labels_json='["Electoral Operations"]'))
  db.commit()
  p={'id':'11','role':'National Administrator','status':'Active','geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}
  result=social_listening_action(db,p,'campaignOfficerClassificationCorrection',
    {'result_id':232,'expected_version':2,'correction_type':'TOPICS','topics':[],
     'rationale':'No substantive operational evidence in the caption'},'91')
  assert result['saved'] is True
  assert result['assessment_version']==3
  assert result['paid_provider_called'] is False
 finally:db.close()
