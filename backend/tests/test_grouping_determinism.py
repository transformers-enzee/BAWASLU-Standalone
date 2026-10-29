from app.processing_hints import emerging_narrative_candidates,incident_cluster_candidates,classification_contract

def post(i,text,author=None):
    return {'id':str(i),'campaign_id':'1','relevance_label':'RELEVANT',
        'text_content':text,'author_name':author or 'Reporter'+str(i),
        'canonical_url':'https://example.test/'+str(i),'published_at':'2026-10-03'}

def test_narrative_same_result_after_reversing_input_order():
    rows=[post(1,'Daftar pemilih dipertanyakan oleh warga'),
          post(2,'Daftar pemilih perlu pemutakhiran'),
          post(3,'Daftar pemilih dalam pembahasan pemilu')]
    assert emerging_narrative_candidates(rows)==emerging_narrative_candidates(list(reversed(rows)))

def test_incident_same_result_after_reversing_input_order():
    rows=[post(1,'Dugaan daftar pemilih di Riau pada TPS satu'),
          post(2,'Laporan daftar pemilih di Riau pada TPS dua')]
    assert incident_cluster_candidates(rows)==incident_cluster_candidates(list(reversed(rows)))

def test_candidate_absence_does_not_depend_on_watchlist():
    result=classification_contract({'id':'2','campaign_id':'1',
       'relevance_label':'RELEVANT','candidate_signals':[]})
    assert result['candidate_absence_is_valid'] is True
    assert result['requires_watchlist_workflow'] is False
    assert result['candidate_classification']=='NO_CANDIDATE'
