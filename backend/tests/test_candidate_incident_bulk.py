"""No-cost high precision canonical and incident grouping regressions."""
from app.processing_hints import (
    canonical_candidate_candidates,incident_cluster_candidates,
    emerging_narrative_candidates,summarize_scoped_findings)


def row(i,text,author=None,url=None,campaign='A',names=None):
    return {'id':str(i),'campaign_id':campaign,'text_content':text,
            'canonical_url':url or 'https://example.test/'+str(i),
            'author_name':author or 'Account '+str(i),
            'candidate_signals':names or [],'relevance_label':'RELEVANT'}


def test_known_full_aliases_share_provisional_key_but_unknowns_do_not_merge():
    rows=[row(1,'pemilu',names=['Gibran Rakabuming Raka']),
          row(2,'pemilu',names=['gibran rakabuming']),
          row(3,'pemilu',names=['Gibran Different Person'])]
    candidates=canonical_candidate_candidates(rows)
    assert len(candidates)==2
    assert candidates[0]['provisional_candidate_key']==candidates[1]['provisional_candidate_key']
    assert all(x['registry_identity_verified'] is False for x in candidates)


def test_distinct_event_discussions_are_provisional_not_verified():
    rows=[row(1,'Dugaan pelanggaran di Riau: politik uang dilaporkan'),
          row(2,'Warga laporkan dugaan pelanggaran di Riau terkait politik uang')]
    groups=incident_cluster_candidates(rows)
    assert len(groups)==1
    assert groups[0]['incident_province_unverified']=='Riau'
    assert groups[0]['same_incident_verified'] is False
    assert summarize_scoped_findings(rows)['incident_clusters_verified']==0


def test_profile_location_does_not_create_incident_group():
    rows=[row(1,'Akun di Riau membahas politik uang'),
          row(2,'Akun di Riau melaporkan politik uang')]
    assert incident_cluster_candidates(rows)==[]


def test_duplicate_reposts_do_not_become_independent_incident_evidence():
    rows=[row(1,'Dugaan pelanggaran di Riau: politik uang dilaporkan'),
          row(2,'Dugaan pelanggaran di Riau: politik uang dilaporkan')]
    assert incident_cluster_candidates(rows)==[]


def test_clusters_never_cross_campaign_and_distinct_jurisdiction():
    rows=[row(1,'Dugaan pelanggaran di Riau: politik uang dilaporkan'),
          row(2,'Dugaan pelanggaran di Bali: politik uang dilaporkan'),
          row(3,'Dugaan pelanggaran di Riau: politik uang laporan',campaign='B')]
    assert incident_cluster_candidates(rows)==[]


def test_recurring_narrative_requires_three_distinct_sources():
    rows=[row(1,'Daftar pemilih perlu dikaji lagi'),
          row(2,'Daftar pemilih ditanyakan warga'),
          row(3,'Daftar pemilih menuai keluhan')]
    n=emerging_narrative_candidates(rows)
    assert len(n)==1 and n[0]['incident_verified'] is False


def test_absent_account_and_url_cannot_claim_independence():
    rows=[row(1,'Dugaan pelanggaran di Riau: politik uang dilaporkan',author=''),
          row(2,'Dugaan pelanggaran di Riau: politik uang meluas')]
    rows[0]['author_name']=''
    assert incident_cluster_candidates(rows)==[]
