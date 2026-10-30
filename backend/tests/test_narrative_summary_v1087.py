from app.inbox_radar import compile_inbox_findings,narrative_summary

def test_summary_describes_specific_pattern_and_caveat():
    s=narrative_summary('Voter register accuracy',3,{})
    assert 'voter-register accuracy' in s
    assert 'not establish' in s
    assert 'Electoral Operations' not in s
    assert 'gaining attention' not in s

def test_candidate_context_not_an_allegation():
    s=narrative_summary('Candidate nomination process',2,{'Gibran Rakabuming Raka':2})
    assert 'also mention Gibran Rakabuming Raka' in s
    assert 'not itself a violation' in s

def test_recurring_pattern_has_evidence_not_broad_category():
    rows=[{'id':str(i),'campaign_id':'1','relevance_label':'RELEVANT',
        'topic_labels':['Electoral Operations'],'text_content':'Diskusi daftar pemilih tetap.',
        'author_name':'account'+str(i),'canonical_url':'https://example.org/'+str(i)}
        for i in [1,2]]
    results=compile_inbox_findings(rows)
    f=[x for x in results if 'narratives' in x['players']]
    assert len(f)==1
    assert 'voter-register accuracy' in f[0]['summary']
