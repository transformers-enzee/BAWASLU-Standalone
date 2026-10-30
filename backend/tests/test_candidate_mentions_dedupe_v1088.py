from app.processing_hints import normalize_candidate_signals
from app.inbox_radar import compile_inbox_findings

def test_spelling_and_alias_forms_collapse():
    result=normalize_candidate_signals(['Ganjar','Ganjar Pranowo','ganjarpranowo',
        'jokowi','Jokowi','Joko Widodo','Prabowo','prabowo','Gibran','Gibran Rakabuming Raka'])
    assert result==['Ganjar Pranowo','Joko Widodo','Prabowo Subianto','Gibran Rakabuming Raka']

def test_one_person_counted_once_per_source():
    rows=[{'id':'1','campaign_id':'1','relevance_label':'RELEVANT',
      'topic_labels':['Electoral Operations'],
      'normalized_candidate_names':['Ganjar','ganjarpranowo','Ganjar Pranowo','Jokowi','jokowi'],
      'text_content':'Informasi pemilu','author_name':'account','canonical_url':'https://example.org/1'}]
    findings=compile_inbox_findings(rows)
    assert sum(f['actor_mentions'].get('Ganjar Pranowo',0) for f in findings)==1
    assert sum(f['actor_mentions'].get('Joko Widodo',0) for f in findings)==1
    assert not any('ganjarpranowo' in f['actor_mentions'] for f in findings)
