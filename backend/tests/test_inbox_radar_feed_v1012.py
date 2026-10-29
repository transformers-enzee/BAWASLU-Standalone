"""Radar consumes actual saved Inbox sources, not speculative pilot IDs."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app import source_lineage as module
from app import campaigns

def test_feed_reuses_scoped_saved_assessments(monkeypatch):
 monkeypatch.setattr(module,'profile',lambda db,user:{'status':'Active','permissions':{'view_intelligence':True}})
 def fake(db,p,action,data):
  assert action=='campaignIntelligenceInbox'
  assert data['campaign_id']=='91'
  return {'findings':[{'id':'225','campaign_id':'91','assessment_version':4,
    'topic_labels':['BAWASLU Reputation'],'relevance_label':'RELEVANT',
    'public_concern_signals':[{'provenance':'OFFICER_SOURCE_REVIEW'}],
    'text_content':'Source text','canonical_url':'https://example.test/source'},
    {'id':'226','campaign_id':'92','topic_labels':['private']} ]}
 monkeypatch.setattr(campaigns,'campaign_action',fake)
 result=module.inbox_radar_feed('91',SimpleNamespace(id=1),None)
 assert result['entry_count']==1
 assert result['entries'][0]['canonical_source_id']=='social:225'
 assert result['entries'][0]['assessment_version']==4
 assert result['entries'][0]['public_concern_signals'][0]['provenance']=='OFFICER_SOURCE_REVIEW'
 assert result['historical_radar_pilot_id_mapping']=='NOT_ATTEMPTED'
 assert result['paid_provider_called'] is False

def test_feed_rejects_non_viewer_and_out_of_scope(monkeypatch):
 monkeypatch.setattr(module,'profile',lambda db,user:{'status':'Inactive','permissions':{'view_intelligence':True}})
 with pytest.raises(HTTPException) as e:
  module.inbox_radar_feed('91',SimpleNamespace(id=1),None)
 assert e.value.status_code==403
 monkeypatch.setattr(module,'profile',lambda db,user:{'status':'Active','permissions':{'view_intelligence':True}})
 monkeypatch.setattr(campaigns,'campaign_action',lambda *a,**k: (_ for _ in ()).throw(PermissionError()))
 with pytest.raises(HTTPException) as e:
  module.inbox_radar_feed('91',SimpleNamespace(id=1),None)
 assert e.value.status_code==403
