from app.auto_relevance import structured_location_signals

def test_province_country_unknown():
    signals=structured_location_signals(['Sumatera Barat','Indonesia','Unknown place'])
    assert signals[0]['province']=='Sumatera Barat'
    assert 'regency_city' not in signals[0]
    assert signals[1:] == ['Indonesia','Unknown place']

def test_valid_explicit_pair():
    locations=structured_location_signals([{'province':'Sumatera Barat','regency_city':'Kota Padang'}])
    assert locations[0]['province']=='Sumatera Barat'
    assert locations[0]['regency_city']=='Kota Padang'

def test_regency_province_mismatch_not_assigned():
    signals=structured_location_signals([{'province':'Sumatera Barat','regency_city':'Kota Bandung'}])
    assert signals[0]['province']=='Sumatera Barat'
    assert 'regency_city' not in signals[0]

def test_invalid_province_not_assigned():
    assert structured_location_signals([{'province':'Invalid province','regency_city':'Kota Padang'}])==[]
