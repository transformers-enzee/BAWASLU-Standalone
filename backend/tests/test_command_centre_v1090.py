"""Command Centre v109.0: grounded player summaries and sentiment/geo lineage."""
from app.inbox_radar import compile_inbox_findings

def post(i,**kw):
    base={'id':str(i),'campaign_id':'1','relevance_label':'RELEVANT','text_content':'Ordinary election post',
    'author_name':'Author '+str(i),'canonical_url':'https://example.org/'+str(i),
    'topic_labels':[],'public_concern_signals':[],'potential_issues':[],'is_flagged':False,
    'sentiment':'UNCLASSIFIED','location_signals':[]}
    base.update(kw)
    return base

def test_violation_summary_describes_actual_source_issue():
    rows=[post(1,is_flagged=True,text_content='Laporan dugaan warga mencoblos lebih dari sekali'),
          post(2,is_flagged=True,text_content='Demo di Bawaslu mengenai kecurangan pemilu')]
    findings=compile_inbox_findings(rows)
    summaries=[f['summary'].lower() for f in findings if 'violations' in f['players']]
    assert len(summaries)==2
    assert any('repeat voting' in summary for summary in summaries)
    assert any('public demonstrations' in summary for summary in summaries)
    assert all('verification' in summary for summary in summaries)

def test_public_concern_uses_saved_officer_description_not_generic_boilerplate():
    row=post(10,public_concern_signals=[{
        'concern':'Voters reported unclear official registration instructions',
        'evidence_quote':'Warga mempertanyakan instruksi pemilih'}])
    f=compile_inbox_findings([row])[0]
    assert 'concerns' in f['players']
    assert 'unclear official registration instructions' in f['summary']
    assert 'need checking' not in f['summary'].lower()

def test_irrelevant_posts_never_contribute_to_dashboard_summaries():
    all_rows=[post(1,is_flagged=True,relevance_label='IRRELEVANT',text_content='Dugaan politik uang'),
              post(2,relevance_label='RELEVANT')]
    f=compile_inbox_findings(all_rows)
    assert len(f)==1
    assert all('violations' not in row['players'] for row in f)

def test_saved_sentiment_and_geography_still_attached_to_same_source():
    row=post(1,sentiment='NEGATIVE',
       location_signals=[{'province':'Nusa Tenggara Timur'}],
       incident_jurisdiction_review={'decision':'UNREVIEWED','incident_jurisdiction_verified':False})
    f=compile_inbox_findings([row])[0]
    assert f['sentiment_counts']=={'NEGATIVE':1}
    assert f['geo_signal_counts']=={'Nusa Tenggara Timur':1}
    assert f['verified_incident_counts']=={}
    assert f['posts'][0]['canonical_source_id']=='social:1'
