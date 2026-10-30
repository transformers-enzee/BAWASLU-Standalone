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

def test_only_multiple_independent_sources_create_recurring_topic_label():
    one=compile_inbox_findings([post(1)])
    assert len(one)==1 and not one[0]['recurring_discussion']
    two=compile_inbox_findings([post(1),post(2)])
    assert len(two)==1 and two[0]['recurring_discussion']
    assert two[0]['supporting_posts']==2

def test_saved_sentiment_and_candidate_mentions_are_reused():
    f=compile_inbox_findings([post(1,normalized_candidate_names=['Candidate A'],sentiment='POSITIVE'),
                              post(2,normalized_candidate_names=['Candidate B'],sentiment='NEGATIVE')])[0]
    assert f['sentiment_counts']=={'POSITIVE':1,'NEGATIVE':1}
    assert f['actor_mentions']=={'Candidate A':1,'Candidate B':1}

def test_previous_review_state_is_reused_without_modifying_assessment():
    key='INBOX-T-'+__import__('hashlib').sha256('electoral operations'.encode()).hexdigest()[:16]
    f=compile_inbox_findings([post(1)],{key:{'status':'monitoring','first_reviewed_at':'2026-10-01'}})[0]
    assert f['status']=='monitoring' and f['human_reviewed']

def test_source_geography_is_not_guessed_from_profile_location():
    f=compile_inbox_findings([post(1)])[0]
    assert f['geography']=='Incident geography not inferred'
    assert f['source_evidence_verified'] is False
