from app.processing_hints import source_hints

def test_topics_are_descriptive_and_multilabel():
    hints=source_hints('KPU mengawasi pemilu. Kritik terhadap Bawaslu muncul.')
    assert hints['topic_suggestions']==['Electoral Operations','BAWASLU Reputation']
    assert hints['incident_jurisdiction_status']=='UNVERIFIED'

def test_location_mentions_do_not_grant_incident_scope():
    hints=source_hints('Akun di Riau menulis tentang Bawaslu Jawa Timur')
    assert hints['province_mentions']==['Jawa Timur','Riau']
    assert hints['province_mentions_are_incident_location'] is False

def test_exact_duplicate_fingerprint_normalizes_whitespace_case():
    assert source_hints('  BAWASLU  RIau ')['exact_text_fingerprint']==source_hints('bawaslu riau')['exact_text_fingerprint']
    assert source_hints('')['exact_text_fingerprint'] is None

def test_no_automatic_violation_or_sentiment_claim():
    hints=source_hints('Ada dugaan pelanggaran pemilu di Riau.')
    assert 'sentiment' not in hints
    assert 'violation_confirmed' not in hints

def test_greeting_is_reviewable_routine_not_electoral_incident():
    text='Selamat Hari Sumpah Pemuda ke-98 Tahun, bersatulah seluruh Pemuda Indonesia! #Bawaslu #BawasluSBB'
    result=source_hints(text)
    assert result['communication_context']['category']=='ROUTINE_COMMUNICATION'
    assert result['communication_context']['actionability']=='NOT_ESTABLISHED'
    assert not result['topic_suggestions']

def test_incident_greeting_mixed_content_not_suppressed():
    result=source_hints('Selamat hari ini. Ada laporan dugaan pelanggaran pemilu di Riau')
    assert result['communication_context']['category']=='UNRESOLVED'
    assert result['incident_jurisdiction_status']=='UNVERIFIED'

def test_routine_relevant_requires_human_relevance_review():
    from app.processing_hints import triage_disposition
    text='Selamat Hari Sumpah Pemuda ke-98 Tahun #Bawaslu'
    assert triage_disposition(text,'RELEVANT')=='REVIEW_RELEVANCE'
    assert triage_disposition(text,'IRRELEVANT')=='NOT_AI_RELEVANT'
    assert triage_disposition('Dugaan pelanggaran pemilu di Riau','RELEVANT')=='RELEVANT_REVIEWED_BY_AI'

def test_candidate_alias_normalization_preserves_unknown_names():
    from app.processing_hints import normalize_candidate_signals
    result=normalize_candidate_signals([{'name':'Gibran Rakabuming'},'gibran rakabuming raka','Unrecognized Person'])
    assert result==['Gibran Rakabuming Raka','Unrecognized Person']

def test_legal_screening_phrase_does_not_claim_violation_or_sentiment():
    from app.processing_hints import classification_evidence
    result=classification_evidence('Laporan dugaan pelanggaran pemilu di Riau')
    assert 'dugaan pelanggaran' in result['potential_issue_phrase_matches']
    assert result['potential_violation_confirmed'] is False
    assert result['sentiment']=='UNCLASSIFIED'

def test_incident_geography_remains_unverified_after_issue_screening():
    result=source_hints('Dugaan pelanggaran di Riau')
    assert result['province_mentions']==['Riau']
    assert result['incident_jurisdiction_status']=='UNVERIFIED'
    assert result['issue_screening']['potential_violation_confirmed'] is False

def test_scoped_classification_aggregation_is_read_only_and_conservative():
    from app.processing_hints import summarize_scoped_findings,source_hints
    a={'id':'10','campaign_id':'1','canonical_url':'https://example.org/a',
       'text_content':'KPU pengawasan pemilu di Riau','potential_issues':[],
       'processing_hints':source_hints('KPU pengawasan pemilu di Riau')}
    b={**a,'id':'11'}
    c={'id':'12','campaign_id':'2','canonical_url':'https://example.org/a',
       'text_content':'dugaan pelanggaran','potential_issues':[{'category_name':'Preliminary'}]}
    result=summarize_scoped_findings([a,b,c])
    assert result['visible_relevant_count']==3
    assert result['exact_duplicate_groups']==[{'campaign_id':'1','source_ids':['10','11'],'basis':'EXACT_NORMALIZED_TEXT'}]
    assert result['topic_groups'][0]['status']=='KEYWORD_GROUP_ONLY'
    assert result['needs_attention_candidates'][0]['result_id']=='12'
    assert result['incident_clusters_verified']==0
    assert result['narratives_verified']==0
    assert result['paid_provider_called'] is False

def test_five_players_only_use_stored_review_evidence():
    from app.processing_hints import summarize_scoped_findings
    rows=[{'id':'20','campaign_id':'1','text_content':'People are concerned about an election',
           'potential_issues':[],'is_flagged':False},
          {'id':'21','campaign_id':'1','text_content':'Alleged violation',
           'potential_issues':[{'category_name':'Election Administration'}],
           'is_flagged':True,'flag_review_status':'FURTHER_INVESTIGATION'}]
    result=summarize_scoped_findings(rows)
    players=result['intelligence_players']
    assert len(players)==5
    assert players['Potential Violations']['count']==1
    assert players['Needs Attention']['count']==1
    assert players['Reviewed History']['count']==1
    assert players['Public Concerns']['count']==0
    assert players['Emerging Narratives']['count']==0
    assert result['player_classification_scope']=='EXISTING_SIGNALS_AND_REVIEWS_ONLY'

def test_assessment_quality_snapshot_does_not_invent_sentiment():
    from app.processing_hints import assessment_quality_snapshot
    rows=[{'id':'1','sentiment':'NEGATIVE','potential_issues':[{'category_name':'Test'}],
           'candidate_signals':[{'name':'Example'}]},
          {'id':'2','sentiment':'UNKNOWN','potential_issues':[]},
          {'id':'3','sentiment':'Neutral','incident_jurisdiction_verified':False}]
    snapshot=assessment_quality_snapshot(rows)
    assert snapshot['sentiment_counts']=={'POSITIVE':0,'NEUTRAL':1,'NEGATIVE':1,'UNCLASSIFIED':1}
    assert snapshot['posts_with_existing_issue_signals']==1
    assert snapshot['posts_with_candidate_signals']==1
    assert snapshot['verified_incident_jurisdiction_posts']==0
    assert snapshot['paid_provider_called'] is False

def test_classification_contract_and_exact_grouping():
    from app.processing_hints import classification_contract,exact_source_groups
    item={'id':'1','campaign_id':'1','relevance_label':'RELEVANT',
          'sentiment':'NEGATIVE','candidate_signals':[{'name':'Gibran Rakabuming'}],
          'text_content':'Riau','canonical_url':'https://example.org/a'}
    result=classification_contract(item)
    assert result['candidate_names']==['Gibran Rakabuming Raka']
    assert result['location_mentions_unverified']==['Riau']
    assert result['sentiment']=='NEGATIVE'
    groups=exact_source_groups([item,{**item,'id':'2'},{**item,'id':'3','campaign_id':'2'}])
    assert len(groups)==1
    assert groups[0]['post_ids']==['1','2']
    assert groups[0]['incident_verified'] is False

def test_batch_preview_routes_and_never_spends_provider_credits():
    from pathlib import Path
    from app import campaigns,socialcrawl
    source=Path(campaigns.__file__).read_text(encoding='utf-8')
    routing=Path(socialcrawl.__file__).read_text(encoding='utf-8')
    part=source.split("if action=='campaignClassificationBatchPreview':",1)[1].split("if action=='campaignIntelligenceInbox':",1)[0]
    assert 'campaignClassificationBatchPreview' in routing
    assert '_result_in_scope(db,p,post)' in part
    assert "classification_writes':0" in part
    assert "paid_provider_called':False" in part
    assert 'assessment_version.desc()' in part

def test_development_classification_preview_is_strictly_bounded():
    from pathlib import Path
    from app import campaigns
    source=Path(campaigns.__file__).read_text(encoding='utf-8')
    body=source.split("if action=='campaignClassificationBatchPreview':",1)[1].split("if action=='campaignIntelligenceInbox':",1)[0]
    assert "sample_limit',10" in body
    assert '1<=sample_limit<=20' in body
    assert '.limit(sample_limit)' in body
    assert "'paid_provider_called':False" in body
    assert "'classification_writes':0" in body

def test_duplicate_text_across_distinct_urls_and_transitive_groups():
    from app.processing_hints import exact_source_groups
    records=[
        {'id':'1','campaign_id':'1','canonical_url':'https://a.test/one','text_content':'Same body'},
        {'id':'2','campaign_id':'1','canonical_url':'https://a.test/two','text_content':' same   BODY '},
        {'id':'3','campaign_id':'1','canonical_url':'https://a.test/two','text_content':'Different body'},
        {'id':'4','campaign_id':'2','canonical_url':'https://a.test/two','text_content':'Same body'},
    ]
    groups=exact_source_groups(records)
    assert len(groups)==1
    assert groups[0]['post_ids']==['1','2']
    assert groups[0]['incident_verified'] is False

def test_keyword_topics_do_not_infer_reputation_from_generic_bawaslu_mention():
    from app.processing_hints import source_hints
    greeting=source_hints('Selamat Hari Sumpah Pemuda #Bawaslu')
    assert greeting['topic_suggestions']==[]
    election=source_hints('KPU memulai pengawasan pemilu di Jawa Timur')
    assert 'Electoral Operations' in election['topic_suggestions']

def test_candidate_whitespace_is_normalized_without_merging_distinct_people():
    from app.processing_hints import normalize_candidate_signals
    result=normalize_candidate_signals(['  Gibran   Rakabuming  Raka  ',
        'Gibran Rakabuming Raka', 'Gibran Another Person'])
    assert result==['Gibran Rakabuming Raka','Gibran Another Person']

def test_issue_phrase_matching_recognizes_word_boundaries_without_confirming_violation():
    from app.processing_hints import classification_evidence
    result=classification_evidence('Ada dugaan pelanggaran dan politik uang.')
    assert result['potential_issue_phrase_matches']==['dugaan pelanggaran','politik uang']
    assert result['potential_violation_confirmed'] is False
    assert classification_evidence('bukanpolitik uangan')['potential_issue_phrase_matches']==[]

def test_summary_duplicate_groups_match_transitive_source_components():
    from app.processing_hints import summarize_scoped_findings
    records=[
        {'id':'1','campaign_id':'1','canonical_url':'https://a.test/a','text_content':'same'},
        {'id':'2','campaign_id':'1','canonical_url':'https://a.test/b','text_content':' SAME '},
        {'id':'3','campaign_id':'1','canonical_url':'https://a.test/b','text_content':'different'},
        {'id':'4','campaign_id':'2','canonical_url':'https://a.test/b','text_content':'same'},
    ]
    summary=summarize_scoped_findings(records)
    assert summary['exact_duplicate_groups']==[
        {'campaign_id':'1','source_ids':['1','2'],'basis':'EXACT_NORMALIZED_TEXT'}]
    assert summary['exact_source_groups'][0]['incident_verified'] is False

def test_duplicate_ids_in_different_campaigns_do_not_collide():
    from app.processing_hints import exact_source_groups
    rows=[
        {'id':'1','campaign_id':'A','canonical_url':'x','text_content':'a'},
        {'id':'2','campaign_id':'A','canonical_url':'x','text_content':'b'},
        {'id':'1','campaign_id':'B','canonical_url':'y','text_content':'c'},
        {'id':'3','campaign_id':'B','canonical_url':'y','text_content':'d'},
    ]
    groups=exact_source_groups(rows)
    assert groups==[]  # Shared URLs with different content are not exact duplicates

def test_candidate_name_deduplication_is_case_insensitive():
    from app.processing_hints import normalize_candidate_signals
    assert normalize_candidate_signals(['Unknown Person','unknown person'])==['Unknown Person']

def test_readonly_diagnostics_disclose_missing_data_without_claiming_cost_coverage():
    from app.processing_hints import summarize_scoped_findings
    result=summarize_scoped_findings([{'id':'5','campaign_id':'A','text_content':'KPU'}])
    diagnostics=result['processing_diagnostics']
    assert diagnostics['missing_field_counts']['sentiment']==1
    assert diagnostics['missing_field_counts']['canonical_url']==1
    assert diagnostics['failed_classifications_reported'] is False
    assert diagnostics['ai_usage_cost_reported'] is False
    assert result['paid_provider_called'] is False


def test_same_url_distinct_comments_never_auto_merge():
    from app.processing_hints import exact_source_groups,summarize_scoped_findings
    rows=[{'id':'1','campaign_id':'A','canonical_url':'https://example.test/thread',
           'text_content':'Comment supporting the election'},
          {'id':'2','campaign_id':'A','canonical_url':'https://example.test/thread',
           'text_content':'Different comment alleging misconduct'}]
    assert exact_source_groups(rows)==[]
    assert summarize_scoped_findings(rows)['exact_duplicate_groups']==[]

def test_same_content_different_urls_is_duplicate_not_confirmed_incident():
    from app.processing_hints import exact_source_groups
    rows=[{'id':'1','campaign_id':'A','canonical_url':'a','text_content':'Same incident text'},
          {'id':'2','campaign_id':'A','canonical_url':'b','text_content':' same  INCIDENT text '}]
    assert exact_source_groups(rows)==[
        {'campaign_id':'A','post_ids':['1','2'],'incident_verified':False}]

def test_narrative_requires_three_distinct_authors_urls_and_texts():
    from app.processing_hints import emerging_narrative_candidates,summarize_scoped_findings
    rows=[{'id':str(i),'campaign_id':'A','canonical_url':f'https://example.test/{i}',
           'text_content':f'Laporan daftar pemilih nomor {i} dipersoalkan di pemilu',
           'author_name':f'Author {i}','relevance_label':'RELEVANT'}
          for i in range(1,4)]
    candidates=emerging_narrative_candidates(rows)
    assert len(candidates)==1
    assert candidates[0]['anchor']=='Voter register accuracy'
    assert candidates[0]['evidence_independence']=='UNVERIFIED'
    summary=summarize_scoped_findings(rows)
    assert summary['intelligence_players']['Emerging Narratives']['count']==1
    assert summary['narratives_verified']==0

def test_narrative_reposts_and_unassessed_are_not_independent_sources():
    from app.processing_hints import emerging_narrative_candidates
    rows=[{'id':str(i),'campaign_id':'A','canonical_url':f'url{i}',
           'text_content':'Daftar pemilih pemilu perlu diteliti',
           'author_name':f'Author {i}','relevance_label':'RELEVANT'}
          for i in range(1,4)]
    assert emerging_narrative_candidates(rows)==[]
    rows[2]['text_content']='Daftar pemilih pemilu perlu diteliti kembali'
    rows[2]['relevance_label']='UNASSESSED'
    assert emerging_narrative_candidates(rows)==[]

def test_dismissed_violations_do_not_reappear_in_attention_queue():
    from app.processing_hints import summarize_scoped_findings
    row={'id':'5','campaign_id':'A','text_content':'dugaan pelanggaran',
         'potential_issues':[{'category_name':'Unverified'}],
         'flag_review_status':'FLAG_DISMISSED','is_flagged':True}
    summary=summarize_scoped_findings([row])
    assert summary['intelligence_players']['Needs Attention']['count']==0
    assert summary['intelligence_players']['Potential Violations']['count']==0
    assert summary['intelligence_players']['Reviewed History']['count']==1

def test_routine_election_greeting_does_not_create_topic_or_narrative():
    from app.processing_hints import source_hints
    hints=source_hints('Selamat Hari Pemilu! #Bawaslu')
    assert hints['topic_suggestions']==[]
    assert hints['narrative_anchors']==[]
