from app.issue_signals import validated_actor_issue_signals

C={4:'Electoral Violation'}

def test_formal_complaint_can_be_flagged_with_paraphrased_activity():
    quote='Pengadu menilai terdapat empat dugaan pelanggaran etik oleh KPU, yakni terkait penghambatan akses Bawaslu.'
    signal={'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':quote,'alleged_actor':'KPU','alleged_activity':'alleged obstruction of oversight access'}
    accepted=validated_actor_issue_signals([signal],C,quote)
    assert len(accepted)==1
    assert accepted[0]['attribution_status']=='SOURCE_ALLEGATION_UNVERIFIED'

def test_named_person_elsewhere_not_attributed():
    source='Gibran menghadiri pertemuan. Pengadu menilai terdapat dugaan pelanggaran etik oleh KPU.'
    signal={'category_id':4,'signal_type':'POTENTIAL_VIOLATION','evidence_quote':'Pengadu menilai terdapat dugaan pelanggaran etik oleh KPU.','alleged_actor':'Gibran','alleged_activity':'ethics violation'}
    assert validated_actor_issue_signals([signal],C,source)==[]

def test_general_mention_without_specific_allegation_is_not_autoflagged():
    source='KPU mengumumkan jadwal pemilu.'
    assert validated_actor_issue_signals([],C,source)==[]
