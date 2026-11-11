"""Smart Radar operational feed must reuse actual Inbox evidence, not pilot sources."""
from app.inbox_radar import compile_inbox_findings,live_inbox_findings

def post(id,campaign_id='1',**kw):
    return {'id':str(id),'campaign_id':campaign_id,'relevance_label':'RELEVANT',
      'text_content':'Recorded source post '+str(id),'canonical_url':'https://news.example/'+str(id),
      'author_name':'source'+str(id),'platform':'X','published_at':'2026-10-29',
      'assessment_version':2,'sentiment':'NEGATIVE','topic_labels':['Electoral Operations'],**kw}

def test_irrelevant_and_unassessed_never_reach_radar():
    out=compile_inbox_findings([post(1),post(2,relevance_label='IRRELEVANT'),post(3,relevance_label='UNASSESSED')])
    assert sum(f['supporting_posts'] for f in out)==1
    assert out[0]['source_ids']==['social:1']

def test_inbox_is_the_only_authoritative_query(monkeypatch):
    from app import campaigns
    observed=[]
    def action(db,p,kind,data):
        observed.append((kind,data))
        return {'findings':[post(42)]}
    monkeypatch.setattr(campaigns,'campaign_action',action)
    findings,inbox=live_inbox_findings(None,{},states={})
    assert observed==[('campaignIntelligenceInbox',{})]
    assert findings[0]['posts'][0]['canonical_source_id']=='social:42'

def test_one_original_source_not_double_counted_across_authorized_campaigns():
    findings=compile_inbox_findings([post(1,campaign_id='1'),post(1,campaign_id='2'),post(2)])
    assert sum(f['supporting_posts'] for f in findings)==2
    assert {p['canonical_source_id'] for f in findings for p in f['posts']}=={'social:1','social:2'}

def test_saved_flag_gets_its_own_source_finding_with_version_and_source_url():
    rows=[post(1,is_flagged=True,potential_issues=[{'category_name':'Reported violation'}],
         flag_review_status=None),
        post(2,is_flagged=True,potential_issues=[{'category_name':'Reported violation'}],
         flag_review_status='FURTHER_INVESTIGATION')]
    items=compile_inbox_findings(rows)
    assert len(items)==2
    assert all('violations' in f['players'] and f['status']=='pending' for f in items)
    assert all(f['supporting_posts']==1 for f in items)
    assert items[0]['posts'][0]['assessment_version']==2

def test_dismissed_flag_not_raised_as_a_new_violation():
    f=compile_inbox_findings([post(1,is_flagged=True,flag_review_status='FLAG_DISMISSED')])
    assert all('violations' not in x['players'] for x in f)

def test_spreadsheet_category_alone_does_not_create_violation_flag():
    f=compile_inbox_findings([post(1,topic_labels=['Allegations / Violations'],is_flagged=False)])
    assert len(f)==1
    assert 'violations' not in f[0]['players']

def test_only_specific_repeated_source_pattern_creates_narrative():
    one=compile_inbox_findings([post(1)])
    assert len(one)==1 and not one[0]['recurring_discussion']
    unclassified=compile_inbox_findings([post(1),post(2)])
    assert len(unclassified)==2
    assert all('narratives' not in f['players'] for f in unclassified)
    two=compile_inbox_findings([
        post(1,text_content='Discussion on daftar pemilih tetap'),
        post(2,text_content='Questions about daftar pemilih tetap')])
    assert len(two)==1 and two[0]['recurring_discussion']
    assert two[0]['supporting_posts']==2

def test_saved_sentiment_and_candidate_mentions_are_reused():
    f=compile_inbox_findings([
        post(1,text_content='Daftar pemilih tetap update',normalized_candidate_names=['Candidate A'],sentiment='POSITIVE'),
        post(2,text_content='Daftar pemilih tetap discussed',normalized_candidate_names=['Candidate B'],sentiment='NEGATIVE')])[0]
    assert f['sentiment_counts']=={'POSITIVE':1,'NEGATIVE':1}
    assert f['actor_mentions']=={'Candidate A':1,'Candidate B':1}

def test_previous_review_state_is_reused_without_modifying_assessment():
    key='INBOX-N-'+__import__('hashlib').sha256('voter register accuracy'.encode()).hexdigest()[:16]
    f=compile_inbox_findings([post(1,text_content='Discussion daftar pemilih tetap'),
                              post(2,text_content='Questions on daftar pemilih tetap')],
                             {key:{'status':'monitoring','first_reviewed_at':'2026-10-01'}})[0]
    assert f['status']=='monitoring' and f['human_reviewed']

def test_source_geography_is_not_guessed_from_profile_location():
    f=compile_inbox_findings([post(1)])[0]
    assert f['geography']=='Incident geography not inferred'
    assert f['source_evidence_verified'] is False

def test_province_counts_use_only_matching_sources_and_candidates():
    data=[
        post(195,text_content='Discussion daftar pemilih tetap',normalized_candidate_names=['Gibran Rakabuming Raka'],
             sentiment='POSITIVE',location_signals=[{'name':'Nusa Tenggara Timur','province':'Nusa Tenggara Timur'}]),
        post(196,text_content='Another daftar pemilih tetap discussion',normalized_candidate_names=['Ganjar Pranowo'],
             sentiment='NEGATIVE',location_signals=[{'name':'Nusa Tenggara Timur','province':'Nusa Tenggara Timur'}]),
        post(197,text_content='Third daftar pemilih tetap discussion',normalized_candidate_names=['Prabowo Subianto'],
             sentiment='NEUTRAL',location_signals=[{'name':'Riau','province':'Riau'}])]
    items=compile_inbox_findings(data)
    grouped=next(x for x in items if x['supporting_posts']==3)
    ntt=grouped['province_breakdown']['Nusa Tenggara Timur']
    assert ntt['supporting_posts']==2
    assert ntt['sentiment_counts']=={'POSITIVE':1,'NEGATIVE':1}
    assert ntt['actor_mentions']=={'Gibran Rakabuming Raka':1,'Ganjar Pranowo':1}
    assert ntt['day_counts']['2026-10-29']==2
    assert grouped['province_breakdown']['Riau']['supporting_posts']==1


def test_discover_only_allows_socialcrawl_host_and_maps_topic_stance():
    from app.prism_discover import safe_url,STANCE
    import pytest
    assert safe_url('/v1/prism/discover').startswith('https://www.socialcrawl.dev/')
    with pytest.raises(ValueError):
        safe_url('https://socialcrawl.dev.attacker.example/v1/prism/discover')
    assert STANCE['positive']=='POSITIVE'
    assert STANCE['no_opinion']=='NEUTRAL'


def test_cross_campaign_duplicate_preserves_authorized_violation_signal_in_any_order():
    # An unrelated non-flagged campaign assessment must not hide a flagged
    # saved assessment of the same underlying SOCIAL post.
    plain=post(475,campaign_id='1',is_flagged=False,assessment_version=2)
    flagged=post(475,campaign_id='4',is_flagged=True,
                 flag_review_status='FURTHER_INVESTIGATION',assessment_version=3)
    for rows in ([plain,flagged],[flagged,plain]):
        output=compile_inbox_findings(rows)
        assert sum(x['supporting_posts'] for x in output)==1
        assert len(output)==1
        assert 'violations' in output[0]['players']
        assert output[0]['posts'][0]['campaign_id']=='4'
        assert output[0]['posts'][0]['review_status']=='FURTHER_INVESTIGATION'


def test_dismissal_in_one_campaign_does_not_silence_separate_flagged_campaign():
    dismissed=post(476,campaign_id='1',is_flagged=True,flag_review_status='FLAG_DISMISSED')
    flagged=post(476,campaign_id='4',is_flagged=True,flag_review_status='FLAG_CONFIRMED')
    output=compile_inbox_findings([dismissed,flagged])
    assert len(output)==1 and 'violations' in output[0]['players']
    assert output[0]['posts'][0]['campaign_id']=='4'
    assert output[0]['posts'][0]['review_status']=='FLAG_CONFIRMED'


def test_command_centre_platform_labels_match_inbox_full_statistics():
    rows=[post(701,platform='twitter-ai-search'),
          post(702,platform='twitter'),
          post(703,platform='tiktok'),
          post(704,platform='instagram'),
          post(705,platform='online_news')]
    findings=compile_inbox_findings(rows)
    from collections import Counter
    counts=Counter(p['platform'] for finding in findings for p in finding['posts'])
    assert counts=={'X':2,'TikTok':1,'Instagram':1,'News':1}


def test_demokrasi_is_not_mistaken_for_a_demonstration_in_gibran_document_report():
    # Regression based on staging finding INBOX-V-5-740. The original news post
    # discusses Gibran's education-certificate dispute and democratic integrity,
    # not a public demonstration.
    article=('Suket Gibran Dinyatakan Tidak Sah oleh MA, PKS: Pansus Harus Segera '
             'Dibentuk. Ini berkaitan dengan integritas proses demokrasi dan '
             'kepercayaan masyarakat terhadap negara.')
    finding=compile_inbox_findings([post(740,campaign_id='5',
        text_content=article,is_flagged=True,flag_review_status='FURTHER_INVESTIGATION',
        potential_issues=[{'category_name':'Potential Violation'}])])[0]
    assert finding['source_ids']==['social:740']
    assert finding['posts'][0]['message_original']==article
    assert 'Demonstrations' not in finding['title']
    assert 'public demonstrations' not in finding['summary']
    assert 'Gibran Education Documents' in finding['title']
    assert 'violations' in finding['players']


def test_actual_demonstration_still_produces_demonstration_specific_finding():
    row=post(741,text_content='Demo di depan kantor Bawaslu menuntut transparansi pemilu',
             is_flagged=True,potential_issues=[{'category_name':'Potential Violation'}])
    finding=compile_inbox_findings([row])[0]
    assert finding['title']=='Demonstrations Questioning Election Oversight'
    assert 'public demonstrations' in finding['summary']
    row2=post(742,text_content='Demonstrasi di Bawaslu terkait hasil pengawasan',
              is_flagged=True,potential_issues=[{'category_name':'Potential Violation'}])
    assert 'Demonstrations' in compile_inbox_findings([row2])[0]['title']


def test_saved_gibran_education_document_dispute_gets_source_grounded_title_and_summary():
    source=('Suket Gibran Dinyatakan Tidak Sah oleh MA, PKS: Pansus Harus Segera Dibentuk. '
            'MA melalui Putusan Nomor 742 K/TUN/2026 mengabulkan kasasi penggugat '
            'dan menyatakan surat keterangan penyetaraan pendidikan SMA Gibran tidak sah. '
            'Teks ini berkaitan dengan integritas proses demokrasi.')
    finding=compile_inbox_findings([post(740,campaign_id='5',
        text_content=source,sentiment='NEGATIVE',is_flagged=True,
        potential_issues=[{'category_name':'Election Administration',
            'signal_type':'REPORTED_INCIDENT',
            'evidence_quote':'surat keterangan penyetaraan pendidikan SMA Gibran tidak sah'}])])[0]
    assert finding['id']=='INBOX-V-5-740'
    assert finding['title']=='Reported Dispute Over Gibran Education Documents'
    assert 'questions about Gibran candidate education documents' in finding['summary']
    assert 'public demonstrations' not in finding['summary']
    assert finding['posts'][0]['sentiment']=='NEGATIVE'
    assert finding['sentiment_counts']=={'NEGATIVE':1}


def test_command_centre_source_drawer_displays_saved_sentiment_instead_of_hardcoded_value():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    html=(root/'frontend/public/ui-freeze/smart-radar-v6_2.html').read_text(encoding='utf-8')
    script=(root/'frontend/public/ui-freeze/smart-radar-live.js').read_text(encoding='utf-8')
    assert "Sentiment: Not classified" not in html
    assert "[String(p[6]||'').toUpperCase()]" in html
    assert "'NEGATIVE','" not in html or "NEGATIVE:'Negative'" in html
    assert "post.sentiment || 'UNCLASSIFIED'" in script
    assert "Potential violation: Preliminary topic signal" not in html
