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
