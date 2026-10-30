"""Regression: issue-specific Command Centre titles, build 109.7."""
from app.inbox_radar import compile_inbox_findings

def post(i, **changes):
    row={'id':str(i),'campaign_id':'1','relevance_label':'RELEVANT',
         'text_content':'','author_name':'Author '+str(i),
         'canonical_url':'https://example.org/'+str(i),
         'topic_labels':[],'public_concern_signals':[],'potential_issues':[],
         'is_flagged':False}
    row.update(changes)
    return row

def test_distinct_saved_violation_issues():
    rows=[
        post(177,is_flagged=True,text_content='Dugaan mencoblos lebih dari sekali',
             potential_issues=[{'category_name':'Electoral Violation'}]),
        post(199,is_flagged=True,text_content='Demo di Bawaslu tentang pengawasan pemilu',
             potential_issues=[{'category_name':'Electoral Violation'}]),
        post(225,is_flagged=True,text_content='Dugaan kecurangan pemilu',
             potential_issues=[{'category_name':'Electoral Violation'}])]
    items={f['id']:f for f in compile_inbox_findings(rows)}
    assert 'Repeat Voting' in items['INBOX-V-1-177']['title']
    assert 'Demonstrations' in items['INBOX-V-1-199']['title']
    assert 'Irregularities' in items['INBOX-V-1-225']['title']
    assert len({f['title'] for f in items.values()})==3
    assert all(f['supporting_posts']==1 for f in items.values())

def test_repeated_issue_titles_remain_distinct():
    items=compile_inbox_findings([
        post(199,is_flagged=True,text_content='Demo di Bawaslu tentang pemilu'),
        post(225,is_flagged=True,text_content='Demo di Bawaslu tentang pemilu')])
    assert len({f['title'] for f in items})==2
    assert all('Demonstrations' in f['title'] for f in items)

def test_public_concern_uses_recorded_issue():
    item=compile_inbox_findings([post(31,text_content='Questions about voter services',
        public_concern_signals=[{'concern':'Unclear registration instructions for voters'}])])[0]
    assert item['title']=='Public Concern: Voter Registration Information'
    assert 'concerns' in item['players']

def test_recurring_narrative_is_specific():
    items=compile_inbox_findings([
        post(1,text_content='Questions about daftar pemilih tetap',topic_labels=['Electoral Operations']),
        post(2,text_content='Discussion about daftar pemilih tetap',topic_labels=['Electoral Operations'])])
    assert len(items)==1
    assert items[0]['title'].startswith('Emerging Narrative: ')
    assert 'Voter register accuracy' in items[0]['title']
    assert items[0]['supporting_posts']==2


def test_absent_saved_topic_does_not_invent_recurring_narrative():
    items=compile_inbox_findings([
        post(1,text_content='Questions about daftar pemilih tetap'),
        post(2,text_content='Discussion about daftar pemilih tetap')])
    assert len(items)==2
    assert all('narratives' not in item['players'] for item in items)
