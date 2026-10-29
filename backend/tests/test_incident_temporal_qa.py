"""Zero-credit incident temporal separation and evidence coverage."""
from app.processing_hints import incident_cluster_candidates,processing_acceptance_snapshot

def post(i,when):
    return {'id':str(i),'campaign_id':'A','relevance_label':'RELEVANT',
            'author_name':'Reporter '+str(i),'canonical_url':'https://test/'+str(i),
            'published_at':when,'candidate_signals':[],
            'text_content':'Dugaan pelanggaran di Riau terkait politik uang laporan '+str(i)}

def test_incidents_from_different_months_remain_separate():
    assert incident_cluster_candidates([post(1,'2024-01-03'),post(2,'2025-01-03')])==[]

def test_same_month_incident_candidates_are_still_unverified():
    result=incident_cluster_candidates([post(1,'2024-01-03'),post(2,'2024-01-11')])
    assert len(result)==1
    assert result[0]['publication_month']=='2024-01'
    assert result[0]['same_incident_verified'] is False

def test_undated_posts_cannot_be_mixed_with_dated_posts():
    assert incident_cluster_candidates([post(1,''),post(2,'2024-01-11')])==[]

def test_acceptance_reports_candidate_signal_coverage_as_zero():
    report=processing_acceptance_snapshot([post(1,'2024-01-03')])
    assert report['posts_with_saved_candidate_signals']==0
    assert report['posts_with_explicit_incident_month']==1
    assert report['confirmed_candidate_identities']==0
