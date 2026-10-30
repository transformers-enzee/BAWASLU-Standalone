"""Operational classification parity regressions."""
from app.inbox_radar import compile_inbox_findings

def row(id,**overrides):
    record={'id':str(id),'campaign_id':'1','relevance_label':'RELEVANT',
      'published_at':'2026-10-29','text_content':'Community electoral concern',
      'canonical_url':'https://example.org/'+str(id),'author_name':'Author '+str(id),
      'topic_labels':[],'public_concern_signals':[],'is_flagged':False,
      'flag_review_status':None}
    record.update(overrides);return record

def test_all_flagged_posts_are_visible_in_operational_perspective():
    items=compile_inbox_findings([row(1,is_flagged=True),row(2,is_flagged=True,topic_labels=['BAWASLU Reputation']),row(3,is_flagged=True)])
    flags=[f for f in items if 'violations' in f['players'] and 'operations' in f['perspectives']]
    assert len(flags)==3
    assert sum(f['supporting_posts'] for f in flags)==3

def test_public_concern_from_a_violation_is_still_a_concern():
    items=compile_inbox_findings([row(1,is_flagged=True,public_concern_signals=[{'concern':'Public dissatisfaction'}],topic_labels=['BAWASLU Reputation'])])
    assert len(items)==1
    assert {'violations','concerns'}.issubset(set(items[0]['players']))
    assert 'operations' in items[0]['perspectives']

def test_relevant_without_topic_is_not_an_emerging_narrative():
    items=compile_inbox_findings([row(i) for i in range(1,20)])
    assert sum('narratives' in f['players'] for f in items)==0
    assert len(items)==19

def test_genuine_saved_topic_remains_a_discussion_not_confirmed_incident():
    f=compile_inbox_findings([row(1,topic_labels=['Electoral Operations']),row(2,topic_labels=['Electoral Operations'])])
    assert len(f)==1 and f[0]['players']==['narratives']
    assert f[0]['recurring_discussion']
