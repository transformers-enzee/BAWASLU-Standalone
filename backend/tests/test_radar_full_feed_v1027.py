"""Complete source reuse contract: scoped, latest saved, no cross-campaign leakage."""
from types import SimpleNamespace
from app import source_lineage,campaigns

def test_inbox_radar_saved_source_round_trip(monkeypatch):
 monkeypatch.setattr(source_lineage,'profile',lambda db,u:{'status':'Active','permissions':{'view_intelligence':True}})
 monkeypatch.setattr(campaigns,'campaign_action',lambda db,p,action,data:{
  'findings':[{'id':'225','campaign_id':'1','assessment_version':7,'relevance_label':'RELEVANT',
    'sentiment':'NEGATIVE','topic_labels':['BAWASLU Reputation'],
    'public_concern_signals':[{'source_quote':'Source quote'}],
    'text_content':'A substantiated source quote is recorded in this sample of text.',
    'player_summaries':[{'provenance':'GPT6_CHAT_GENERATED_QA_SAMPLE','status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW',
     'source_quote':'A substantiated source quote','summary':'This sample needs human review.'}]},
    {'id':'226','campaign_id':'2','assessment_version':1}]})
 result=source_lineage.inbox_radar_feed('1',SimpleNamespace(id=5),None)
 assert result['entry_count']==1
 row=result['entries'][0]
 assert row['canonical_source_id']=='social:225'
 assert row['assessment_version']==7
 assert row['topic_labels']==['BAWASLU Reputation']
 assert row['summary_verification']['pipeline']==[]
 assert 'player_summaries' not in row
 assert result['source_scope']=='AUTHENTICATED_SAVED_INBOX_ONLY'
 assert result['paid_provider_called'] is False
