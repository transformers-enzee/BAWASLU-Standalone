from app.issue_signals import actor_signal_diagnostic
C={4:'Electoral Violation'}
def test_no_ai_candidates_is_distinguished():
    d=actor_signal_diagnostic([],C,'KPU dilaporkan ke DKPP atas dugaan pelanggaran etik.')
    assert d=={'candidate_count':0,'accepted_count':0,'rejected_reasons':{}}
def test_candidate_rejected_without_quote():
    d=actor_signal_diagnostic([{'category_id':4,'alleged_actor':'KPU','alleged_activity':'penghambatan','evidence_quote':'Unrelated fabricated quote'}],C,'KPU dilaporkan ke DKPP.')
    assert d['candidate_count']==1 and d['accepted_count']==0
    assert d['rejected_reasons']=={'quote_missing_from_source':1}
def test_supported_source_allegation_candidate_is_accepted():
    quote='Pengadu menyebut dugaan pelanggaran etik oleh KPU terkait penghambatan akses Bawaslu.'
    signal={'category_id':4,'signal_type':'POTENTIAL_VIOLATION','alleged_actor':'KPU','alleged_activity':'alleged oversight obstruction','evidence_quote':quote}
    d=actor_signal_diagnostic([signal],C,quote)
    assert d['candidate_count']==1 and d['accepted_count']==1 and d['rejected_reasons']=={}
