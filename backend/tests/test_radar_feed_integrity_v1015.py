"""Radar feed must derive from authorized Inbox saved findings."""
from types import SimpleNamespace
from app import source_lineage
from app import campaigns

def test_radar_feed_ignores_foreign_campaign_and_does_not_invent_mapping(monkeypatch):
 monkeypatch.setattr(source_lineage,'profile',lambda db,u:{'status':'Active','permissions':{'view_intelligence':True}})
 monkeypatch.setattr(campaigns,'campaign_action',lambda db,p,action,data:{
  'findings':[{'id':'12','campaign_id':'42','assessment_version':2,'topic_labels':['Electoral Operations'],
  'public_concern_signals':[],'source_url':'https://example.org/12'},
  {'id':'14','campaign_id':'99','assessment_version':8,'topic_labels':['private']} ]})
 out=source_lineage.inbox_radar_feed('42',SimpleNamespace(id=3),None)
 assert out['entry_count']==1
 assert out['entries'][0]['canonical_source_id']=='social:12'
 assert out['entries'][0]['assessment_version']==2
 assert out['historical_radar_pilot_id_mapping']=='NOT_ATTEMPTED'
 assert out['paid_provider_called'] is False
