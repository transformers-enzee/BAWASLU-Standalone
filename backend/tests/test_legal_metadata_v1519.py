"""v151.9 metadata is recorded but not declared legal approval."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_knowledge import ReviewBody

def doc(kind="PEMILU",version="2022 consolidated",date="2022-10-01"):
    return {"record_id":"DOC-2-P1","record_type":"PDF_KNOWLEDGE",
            "document_type":"REGULATION","review_status":"OFFICER_REVIEWED",
            "title":"Pedoman Pemilu","source_excerpt":"Pasal 21",
            "legal_election_type":kind,"legal_version_label":version,
            "legal_effective_date":date}

def audit(item):
    return audit_assistant_answer("What applies to Pilkada?",[item],
                                  "Pasal 21 [DOC-2-P1].",
                                  profile="PDF_GUIDANCE",language="en")[2]

def test_version_fields_do_not_certify_legal_currentness():
    data=audit(doc("PILKADA"))
    assert data["legal_document_version_metadata_available"] is True
    assert data["legal_document_version_verified"] is False
    assert data["legal_currentness_verified"] is False

def test_missing_version_and_date_are_identified():
    data=audit(doc("PILKADA","",""))
    assert data["legal_document_version_missing_ids"]==["DOC-2-P1"]
    assert data["legal_document_effective_date_missing_ids"]==["DOC-2-P1"]

def test_explicit_election_type_metadata_mismatch_is_flagged():
    data=audit(doc("PEMILU"))
    assert data["legal_election_type_metadata_conflict_ids"]==["DOC-2-P1"]
    assert "LEGAL_ELECTION_SCOPE" in data["legal_review_reason_codes"]

def test_matching_metadata_does_not_approve_applicability():
    data=audit(doc("PILKADA"))
    assert data["legal_election_type_metadata_conflict_ids"]==[]
    assert data["legal_election_type_applicability_verified"] is False

def test_review_body_defaults_to_unverified_scope():
    body=ReviewBody(document_type="REGULATION")
    assert body.legal_election_type=="UNSPECIFIED"
    assert body.legal_version_label==""
    assert body.legal_effective_date==""
