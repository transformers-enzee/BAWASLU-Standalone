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
    assert result['exact_duplicate_groups']==[{'campaign_id':'1','source_ids':['10','11'],'basis':'EXACT_URL_OR_TEXT'}]
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
