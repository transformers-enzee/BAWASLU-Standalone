"""Batch-1 acceptance is a complete, honest four-item readiness matrix."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.access import default_permissions
from app.campaign_acceptance import campaign_acceptance_snapshot

def test_batch_one_all_items_reported_without_fabricated_done():
 db=Session(create_engine('sqlite:///:memory:'))
 try:
  Base.metadata.create_all(db.get_bind())
  db.add(MonitoringCampaign(id=91,name='Batch-1 QA',created_by='1',
     primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
  for i,text in ((1,'Laporan pelanggaran di Jawa Timur diproses.'),
                 (2,'Laporan pelanggaran di Jawa Timur diproses.'),
                 (3,'Warga mempertanyakan daftar pemilih dan meminta penjelasan.')):
   db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
       text_content=text,canonical_url='https://example.test/'+str(i),
       author_name='Officer sample'))
   db.add(CampaignEvidence(campaign_id=91,result_id=i))
  db.add(EvidenceAssessment(campaign_id=91,result_id=1,assessment_version=1,relevance_label='RELEVANT'))
  db.commit()
  p={'id':'1','role':'National Administrator','status':'Active',
    'geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}
  output=campaign_acceptance_snapshot(db,p,'91')
  gates=output['batch1_acceptance']
  assert set(gates)=={'6','8','9','11'}
  assert all(gates[k]['workflow_tested'] for k in gates)
  assert gates['8']['production_state']=='PROPOSAL_READY'
  assert gates['8']['officer_accepted'] is False
  assert gates['9']['officer_accepted'] is False
  assert gates['6']['officer_accepted'] is False
  assert gates['11']['officer_accepted'] is False
  assert output['batch1_all_officer_accepted'] is False
  assert output['batch1_paid_provider_called'] is False
 finally: db.close()
