from app.issue_signals import rejected_issue_signal_reasons

def test_rejection_reason_breakdown():
    source='Warga menyebut dugaan pembagian uang kepada pemilih.'
    signals=[
        {'category_id':2,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':1,'signal_type':'TOPIC','evidence_quote':'pembagian uang kepada pemilih'},
        {'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'short'},
        {'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'kutipan yang tidak ada dalam sumber'},
        {'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'pembagian uang kepada pemilih'},
        None]
    counts=rejected_issue_signal_reasons(signals,{1:'Money politics'},source)
    assert counts=={'invalid_category':1,'invalid_signal_type':1,'missing_or_short_quote':1,'quote_not_in_source':1,'malformed_signal':1}
    assert len(signals)==6

def test_no_false_rejections():
    signal={'category_id':1,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'Pembagian uang kepada pemilih'}
    counts=rejected_issue_signal_reasons([signal],{1:'Money politics'},'Ada pembagian uang kepada pemilih.')
    assert sum(counts.values())==0
