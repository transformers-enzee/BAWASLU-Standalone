from app.inbox_radar import compile_inbox_findings

def row(i,body):
    return {'id':str(i),'campaign_id':'1','relevance_label':'RELEVANT','topic_labels':['Electoral Operations'],'text_content':body,'author_name':'author'+str(i),'canonical_url':'https://example.org/'+str(i),'is_flagged':False,'public_concern_signals':[]}

def themes(rows):
    return [f for f in compile_inbox_findings(rows) if 'narratives' in f['players']]

def test_general_topic_not_a_narrative():
    assert not themes([row(i,'Informasi pemilu umum') for i in range(1,22)])

def test_specific_repeated_pattern():
    result=themes([row(1,'Warga membahas daftar pemilih tetap'),row(2,'Diskusi soal daftar pemilih tetap')])
    assert len(result)==1
    assert result[0]['supporting_posts']==2
    assert 'Voter register accuracy' in result[0]['title']

def test_one_source_not_recurrence():
    assert not themes([row(1,'Diskusi daftar pemilih tetap')])
