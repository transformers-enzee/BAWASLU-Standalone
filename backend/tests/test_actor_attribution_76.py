from app.issue_signals import validated_actor_issue_signals

CATEGORIES={4:'Electoral Violation'}

def test_actor_allegation_is_provisional():
    source='Person B allegedly distributed money to voters.'
    signal={'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':source,'alleged_actor':'Person B','alleged_activity':'distributed money'}
    out=validated_actor_issue_signals([signal],CATEGORIES,source)
    assert len(out)==1
    assert out[0]['alleged_actor']=='Person B'
    assert out[0]['attribution_status']=='SOURCE_ALLEGATION_UNVERIFIED'

def test_author_is_not_assigned_from_source():
    source='Person A reports campaign violations by an unnamed person.'
    signal={'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':source,'alleged_actor':'Person A','alleged_activity':'campaign violations'}
    assert validated_actor_issue_signals([signal],CATEGORIES,source)==[]

def test_no_actor_no_flag():
    source='Campaign policy discussions continue today.'
    assert validated_actor_issue_signals([{'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':source}],CATEGORIES,source)==[]

def test_quote_must_identify_actor_and_activity():
    source='Person B spoke at an event. Reports mention bribery elsewhere.'
    raw={'category_id':4,'signal_type':'POTENTIAL_VIOLATION','alleged_actor':'Person B','alleged_activity':'bribery','evidence_quote':'Person B spoke at an event.'}
    assert validated_actor_issue_signals([raw],CATEGORIES,source)==[]
