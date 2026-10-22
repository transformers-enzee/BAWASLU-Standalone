from types import SimpleNamespace
from app.issue_signals import phrase_screening_candidates

def rec(**x): return SimpleNamespace(**x)

categories=[rec(id=4,name='Electoral Violation',active=True)]
phrases=[rec(category_id=4,phrase='pelanggaran etik',active=True)]

def test_allegation_lead_is_flaggable_and_unverified():
    text='Warga mengadukan dugaan pelanggaran etik dalam proses pencalonan.'
    signals=phrase_screening_candidates(text,categories,phrases)
    assert len(signals)==1
    assert signals[0]['signal_provenance']=='KEYWORD_SCREENING'
    assert signals[0]['requires_human_verification']

def test_plain_mentions_do_not_flag():
    assert phrase_screening_candidates('Diskusi tentang pelanggaran etik.',categories,phrases)==[]

def test_historical_verdict_reporting_does_not_flag():
    text='Majelis hakim menyatakan dugaan pelanggaran etik dalam putusan pengadilan.'
    assert phrase_screening_candidates(text,categories,phrases)==[]

def test_inactive_category_and_phrase_do_not_flag():
    text='Warga melaporkan dugaan pelanggaran etik.'
    assert phrase_screening_candidates(text,[rec(id=4,name='Electoral Violation',active=False)],phrases)==[]
    assert phrase_screening_candidates(text,categories,[rec(category_id=4,phrase='pelanggaran etik',active=False)])==[]
