from types import SimpleNamespace
from app.issue_signals import active_issue_taxonomy, validated_issue_signals

def record(**values):
    return SimpleNamespace(**values)

def test_taxonomy_only_includes_active_categories_and_phrases():
    categories=[record(id=1,name='Money politics',active=True),
                record(id=2,name='Inactive issue',active=False)]
    phrases=[record(category_id=1,phrase='politik uang',active=True),
             record(category_id=1,phrase='old alias',active=False),
             record(category_id=2,phrase='inactive category phrase',active=True)]
    assert active_issue_taxonomy(categories,phrases)==[
        {'id':1,'name':'Money politics','phrases':['politik uang']}]

def test_valid_source_quoted_signal_is_preserved():
    text='Warga melaporkan dugaan pembagian uang kepada pemilih di sebuah acara.'
    signal={'category_id':1,'signal_type':'POTENTIAL_VIOLATION',
            'evidence_quote':'pembagian uang kepada pemilih'}
    actual=validated_issue_signals([signal],{1:'Money politics'},text)
    assert len(actual)==1 and actual[0]['category_name']=='Money politics'

def test_unsupported_or_inactive_category_and_quote_are_rejected():
    text='Diskusi publik tentang debat kandidat.'
    signals=[
        {'category_id':2,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'Diskusi publik tentang debat'},
        {'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'Diskusi'},
        {'category_id':1,'signal_type':'TOPIC_MATCH','evidence_quote':'Diskusi publik tentang debat'},
        {'category_id':True,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'Diskusi publik tentang debat'}]
    assert validated_issue_signals(signals,{1:'Money politics'},text)==[]

def test_case_insensitive_quote_and_non_mutating_output():
    text='Ada DUGAAN PEMBERIAN HADIAH kepada warga.'
    raw={'category_id':1,'signal_type':'POTENTIAL_VIOLATION',
         'evidence_quote':'dugaan pemberian hadiah','explanation':'Requires review'}
    assert validated_issue_signals([raw],{1:'Money politics'},text)[0]['evidence_quote']==raw['evidence_quote']
    assert raw['signal_type']=='POTENTIAL_VIOLATION'

def test_phrase_match_is_not_a_violation_by_itself():
    text='Diskusi publik: politik uang harus dicegah.'
    assert validated_issue_signals([],{1:'Money politics'},text)==[]

def test_malformed_model_output_is_safe():
    assert validated_issue_signals(None,{1:'Money politics'},'Any text')==[]
    assert validated_issue_signals([42,None,'bad'],{1:'Money politics'},'Any text')==[]

def test_legacy_missing_type_requires_active_category_and_source_quote():
    text='Warga melaporkan dugaan pembagian uang kepada pemilih.'
    legacy={'category_id':1,'evidence_quote':'pembagian uang kepada pemilih'}
    original=dict(legacy)
    accepted=validated_issue_signals([legacy],{1:'Money politics'},text)
    assert len(accepted)==1
    assert accepted[0]['signal_provenance']=='LEGACY_MISSING_TYPE'
    assert accepted[0]['requires_human_verification'] is True
    assert legacy==original

def test_legacy_not_accepted_without_supported_quote_or_category():
    text='Berita mengenai proses penghitungan suara.'
    signals=[{'category_id':99,'evidence_quote':'proses penghitungan suara'},
             {'category_id':1,'evidence_quote':'pembagian uang kepada pemilih'},
             {'category_id':1,'evidence_quote':'pendek'},
             {'category_id':1,'signal_type':None,'evidence_quote':'proses penghitungan suara'},
             {'category_id':1,'signal_type':'TOPIC','evidence_quote':'proses penghitungan suara'}]
    assert validated_issue_signals(signals,{1:'Money politics'},text)==[]

def test_legacy_accepted_signals_not_counted_as_rejections():
    from app.issue_signals import rejected_issue_signal_reasons, rejected_issue_type_summary
    signal={'category_id':1,'evidence_quote':'proses penghitungan suara'}
    assert sum(rejected_issue_signal_reasons([signal],{1:'Elections'},'proses penghitungan suara').values())==0
    assert rejected_issue_type_summary([signal],{1:'Elections'},'proses penghitungan suara')=={}
