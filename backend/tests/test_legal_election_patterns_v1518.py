"""v151.8: actual word-boundary matching in election scope classifier."""
from app.assistant_grounding import _election_types, _legal_election_scope

def test_pemilu_explicit_term_detected_without_substring_false_positive():
    assert _election_types("Which Pemilu law applies?")==["PEMILU"]
    assert _election_types("pemiluan")==[]

def test_pilkada_and_regional_election_alias_detected():
    assert _election_types("Pilkada legislation")==["PILKADA"]
    assert _election_types("Pemilihan Kepala Daerah")==["PILKADA"]

def test_scope_compare_flags_opposite_title():
    hints,details,conflicts,unknown=_legal_election_scope(
        "Pemilu rules", [{"record_id":"DOC-1-P2","title":"Peraturan Pilkada"}])
    assert hints==["PEMILU"]
    assert conflicts==["DOC-1-P2"]
    assert unknown==[]

def test_scope_compare_does_not_invent_approval_for_matching_title():
    hints,details,conflicts,unknown=_legal_election_scope(
        "Pilkada rules", [{"record_id":"DOC-1-P2","title":"Peraturan Pilkada"}])
    assert hints==["PILKADA"]
    assert conflicts==[]
    assert details[0]["title_scope"]==["PILKADA"]
