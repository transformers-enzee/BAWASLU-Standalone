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
