"""Parallel zero-credit engineering gates for open items 12, 13, 14."""
import hashlib
from types import SimpleNamespace
from app.summary_readiness import validated_summary_buckets
from app import campaigns,source_lineage,qa_saved_accuracy

def test_12_only_fingerprinted_source_quote_production_draft_is_accepted():
 body='An election officer reports a recorded public concern from a witnessed event.'
 digest=hashlib.sha256(body.encode()).hexdigest()
 draft={'player':'Public Concerns','summary':'A recorded public concern needs independent officer review.',
 'source_quote':'recorded public concern','status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW',
 'provenance':'PRODUCTION_AI_PIPELINE','source_text_sha256':digest}
 assert len(validated_summary_buckets({'text_content':body,'player_summaries':[draft]})['pipeline'])==1
 assert not validated_summary_buckets({'text_content':body+' modified','player_summaries':[draft]})['pipeline']
 assert not validated_summary_buckets({'text_content':body,'player_summaries':[{**draft,'provenance':'QA_EXAMPLE'}]})['pipeline']
 assert not validated_summary_buckets({'text_content':body,'player_summaries':[{**draft,'source_quote':'invented unrelated source quote'}]})['pipeline']

def test_13_cross_module_source_id_reused_without_pilot_crosswalk(monkeypatch):
 monkeypatch.setattr(source_lineage,'profile',lambda db,u:{'status':'Active','permissions':{'view_intelligence':True}})
 monkeypatch.setattr(campaigns,'campaign_action',lambda db,p,a,d:{'findings':[{'id':155,'campaign_id':'1','assessment_version':3,'topic_labels':['Election Operations']}]})
 feed=source_lineage.inbox_radar_feed('1',SimpleNamespace(id=1),None)
 assert feed['entry_count']==1
 assert feed['entries'][0]['canonical_source_id']=='social:155'
 assert feed['entries'][0]['cross_module_lineage']=='SHARED_SOCIAL_SOURCE_ID'
 assert feed['historical_radar_pilot_id_mapping']=='NOT_ATTEMPTED'

def test_14_historical_accuracy_is_measurement_not_new_inference():
 query=str(qa_saved_accuracy.QUERY)
 assert 'qa_ai_assessments' in query
 assert 'qa_imported_human_categories' in query
 assert 'count(*)' in query
 assert 'holdout' in query.lower()
 assert not any(x in query.lower() for x in ('insert into','update ','delete from'))
