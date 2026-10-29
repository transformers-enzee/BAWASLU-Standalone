"""Cross-module source-validated potential-violation regression tests. No paid AI."""
from types import SimpleNamespace
from app.issue_signals import validated_issue_signals, shared_violation_decision, phrase_screening_candidates

def evaluate(text,raw,review=None):
    valid=validated_issue_signals(raw,{4:'Election issue'},text)
    return shared_violation_decision(valid,review),valid

def test_supported_quote_is_unverified():
    result,signals=evaluate('Laporan dugaan pembagian uang kepada pemilih.',[{'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'dugaan pembagian uang kepada pemilih'}])
    assert len(signals)==1 and result['is_flagged']
    assert result['uncertainty_label']=='UNVERIFIED_AI_INDICATOR'
    assert result['human_validation_required']

def test_unsupported_or_malformed_signals_cannot_flag():
    text='Pengumuman pemilu tahun 2026.'
    for raw in ([{'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'dugaan pembagian uang kepada pemilih'}],
                [{'category_id':99,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'Pengumuman pemilu tahun 2026'}],
                [{'category_id':4,'signal_type':'TOPIC','evidence_quote':'Pengumuman pemilu tahun 2026'}],
                [False],['not a signal'],[],None):
        result,signals=evaluate(text,raw)
        assert not result['is_flagged'] and not signals

def test_keywords_are_review_leads_not_automatic_flags():
    assert not shared_violation_decision([{'signal_provenance':'KEYWORD_SCREENING'}])['is_flagged']
    assert phrase_screening_candidates('Edukasi pencegahan politik uang.',
        [SimpleNamespace(id=4,name='Election issue',active=True)],
        [SimpleNamespace(category_id=4,phrase='politik uang',active=True)])==[]

def test_officer_dismissal_supersedes_saved_flag():
    result,signals=evaluate('Laporan dugaan intimidasi terhadap pemilih.',
        [{'category_id':4,'signal_type':'REPORTED_INCIDENT','evidence_quote':'dugaan intimidasi terhadap pemilih'}],'FLAG_DISMISSED')
    assert signals and not result['is_flagged'] and result['uncertainty_label']=='DISMISSED_BY_OFFICER'

def test_officer_review_remains_preliminary():
    for status in ('FLAG_CONFIRMED','FURTHER_INVESTIGATION'):
        result=shared_violation_decision([],status)
        assert result['is_flagged'] and result['uncertainty_label']=='HUMAN_REVIEWED_PRELIMINARY'

def test_historical_incident_is_not_current_allegation():
    result,signals=evaluate('Arsip laporan dugaan politik uang pada pemilu 2024.',
        [{'category_id':4,'signal_type':'REPORTED_INCIDENT','time_context':'HISTORICAL','evidence_quote':'laporan dugaan politik uang pada pemilu 2024'}])
    assert result['is_flagged'] and signals[0]['time_context']=='HISTORICAL'
    assert signals[0]['signal_type']=='REPORTED_INCIDENT'

def test_unknown_review_does_not_override_saved_status():
    result,_=evaluate('Warga melaporkan dugaan manipulasi suara.',
        [{'category_id':4,'evidence_quote':'dugaan manipulasi suara'}],'UNKNOWN')
    assert result['is_flagged'] and result['review_status'] is None
