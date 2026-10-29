"""No-credit shared social-source identity regression for future Radar feed."""
from types import SimpleNamespace
from app import source_lineage,campaigns

def test_radar_reuses_original_identity_without_fake_validation(monkeypatch):
 monkeypatch.setattr(source_lineage,'profile',lambda db,u:{'permissions':{'view_intelligence':True},'status':'Active'})
 monkeypatch.setattr(campaigns,'campaign_action',lambda db,p,action,data:{'findings':[{'id':155,'campaign_id':'1','assessment_version':3,'text_content':'Original source'}]})
 entry=source_lineage.inbox_radar_feed('1',SimpleNamespace(id=1),None)['entries'][0]
 assert entry['canonical_source_id']=='social:155'
 assert entry['source_identity_namespace']=='social'
 assert entry['cross_module_lineage']=='SHARED_SOCIAL_SOURCE_ID'
 assert entry['source_evidence_verified'] is False
 assert entry['human_validation_required'] is True
