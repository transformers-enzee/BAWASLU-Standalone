import pytest
from app.source_ids import canonical_source_id, canonical_candidate_id, parse_canonical_source_id

def test_namespaced_source_ids_are_stable_and_distinct():
    assert canonical_source_id("social", 154) == "social:154"
    assert canonical_source_id("radar", "POST-001") == "radar:POST-001"
    assert parse_canonical_source_id("social:154") == ("social", "154")
    assert canonical_source_id("social", 154) != canonical_source_id("radar", 154)

@pytest.mark.parametrize("namespace, value", [
    ("social", ""), ("social", "a-name"), ("radar", "../bad"),
    ("other", "123"), ("social", "1/2"), ("radar", "space in ID")
])
def test_reject_invalid_and_ambiguous_sources(namespace,value):
    with pytest.raises(ValueError):
        canonical_source_id(namespace, value)

def test_candidate_ids_derive_from_registry_id_not_name():
    assert canonical_candidate_id(7) == "candidate:7"
    assert canonical_candidate_id("0007") == "candidate:7"
    with pytest.raises(ValueError):
        canonical_candidate_id("Candidate Name")
    with pytest.raises(ValueError):
        canonical_candidate_id(0)

@pytest.mark.parametrize("value", ["social:abc","radar:../bad","social:001","missing"])
def test_parse_rejects_noncanonical_ids(value):
    with pytest.raises(ValueError):
        parse_canonical_source_id(value)
