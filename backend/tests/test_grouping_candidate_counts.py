from app.finding_groups import grouping_candidate_counts,propose_groups

def row(i,text,author=None):
    return {'id':str(i),'campaign_id':'4','relevance_label':'RELEVANT',
      'text_content':text,'canonical_url':'https://example.org/'+str(i),
      'author_name':author or 'Author '+str(i),'published_at':'2026-10-03'}

def test_empty_candidate_count_is_valid():
    result=grouping_candidate_counts([])
    assert result['total']==0
    assert result['requires_candidate_identity'] is False
    assert result['legal_findings_verified']==0

def test_duplicates_and_narratives_separately_counted():
    rows=[row(1,'Daftar pemilih perlu diperiksa'),
          row(2,'Daftar pemilih perlu diperiksa'),
          row(3,'Warga bertanya mengenai daftar pemilih')]
    counts=grouping_candidate_counts(rows)
    assert counts['exact_duplicates']>=1
    assert counts['legal_findings_verified']==0
    assert counts['requires_candidate_identity'] is False
