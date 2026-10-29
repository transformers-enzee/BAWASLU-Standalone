from app.processing_hints import processing_acceptance_snapshot

def test_acceptance_gaps_cannot_claim_unverified_ids():
    rows=[{'id':'1','campaign_id':'A','relevance_label':'RELEVANT',
           'candidate_signals':['Distinct New Candidate'],'text_content':'pemilu',
           'author_name':'Account 1','canonical_url':'https://a.test/1'}]
    summary=processing_acceptance_snapshot(rows)
    assert summary['unresolved_candidate_names_count']==1
    assert summary['confirmed_candidate_identities']==0
    assert summary['verified_incidents']==0
    assert summary['paid_ai_calls']==0

def test_assessment_snapshot_ignores_irrelevant_rows_and_handles_missing_text():
    rows=[{'id':'1','campaign_id':'A','relevance_label':'IRRELEVANT',
           'candidate_signals':['Unknown person']},
          {'id':'2','campaign_id':'A','relevance_label':'RELEVANT','text_content':''}]
    summary=processing_acceptance_snapshot(rows)
    assert summary['eligible_posts']==1
    assert summary['unresolved_candidate_names_count']==0
    assert summary['missing_source_text_count']==1
