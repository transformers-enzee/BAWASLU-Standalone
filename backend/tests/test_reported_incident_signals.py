from app.issue_signals import validated_reported_incident_signals, validated_issue_signals

def test_historical_report_is_review_lead_not_actor_accusation():
    src='Bawaslu menerima laporan dugaan politik uang dan intimidasi pada pemilu lalu.'
    raw=[{'category_id':4,'evidence_quote':'Bawaslu menerima laporan dugaan politik uang dan intimidasi',
          'time_context':'HISTORICAL','explanation':'Reported historic complaint'}]
    signals=validated_reported_incident_signals(raw,{4:'Electoral Violation'},src)
    assert len(signals)==1
    assert signals[0]['signal_type']=='REPORTED_INCIDENT'
    assert signals[0]['time_context']=='HISTORICAL'
    assert signals[0]['requires_human_verification']
    assert len(validated_issue_signals(signals,{4:'Electoral Violation'},src))==1

def test_rejects_fabricated_quote_inactive_category_and_invalid_context():
    source='Diskusi tentang pemilu.'
    base={'category_id':4,'evidence_quote':'Bawaslu menerima laporan dugaan politik uang',
          'time_context':'HISTORICAL'}
    assert validated_reported_incident_signals([base],{4:'Electoral Violation'},source)==[]
    assert validated_reported_incident_signals([base],{},base['evidence_quote'])==[]
    assert validated_reported_incident_signals([{**base,'time_context':'FUTURE'}],{4:'Electoral Violation'},base['evidence_quote'])==[]

def test_keyword_alone_does_not_create_reported_incident():
    assert validated_reported_incident_signals([],{4:'Electoral Violation'},'politik uang')==[]
