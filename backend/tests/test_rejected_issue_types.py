from app.issue_signals import rejected_issue_type_summary

def test_counts_distinct_invalid_stored_types_without_accepting_them():
    source='Warga melaporkan dugaan pembagian uang kepada pemilih.'
    signals=[
        {'category_id':1,'signal_type':'LEGACY','evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':1,'signal_type':'LEGACY','evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':1,'evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':2,'signal_type':'OUT_OF_SCOPE','evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'pembagian uang kepada pemilih'}]
    assert rejected_issue_type_summary(signals,{1:'Money politics'},source)=={'LEGACY':2,'(missing)':1}

def test_empty_or_malformed_payload_returns_empty_summary():
    assert rejected_issue_type_summary(None,{1:'Money politics'},'')=={}
    assert rejected_issue_type_summary([None,42],{1:'Money politics'},'')=={}
