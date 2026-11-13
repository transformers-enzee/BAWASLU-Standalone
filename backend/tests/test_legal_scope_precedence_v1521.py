"""v152.1: structured scope precedence, legal-only metadata, review gates."""
import pytest
from fastapi import HTTPException
from app.assistant_grounding import audit_assistant_answer
from app.assistant_knowledge import ReviewBody

def ref(scope,title="Pedoman Pilkada"):
    return {"record_id":"DOC-7-P1","record_type":"PDF_KNOWLEDGE",
            "document_type":"REGULATION","title":title,
            "legal_election_type":scope,"review_status":"OFFICER_REVIEWED",
            "source_excerpt":"Pasal 21","legal_version_label":"", "legal_effective_date":""}

def audit(row):
    return audit_assistant_answer("Which Pemilu rules apply?",[row],
           "Pasal 21 appears [DOC-7-P1].",profile="PDF_GUIDANCE",language="en")[2]

def test_both_scope_resolves_title_only_conflict_without_certifying_applicability():
    x=audit(ref("BOTH"))
    assert x["legal_election_type_title_conflict_ids"]==["DOC-7-P1"]
    assert x["legal_election_type_unresolved_title_conflict_ids"]==[]
    assert x["legal_election_type_scope_review_ids"]==[]
    assert x["legal_election_type_applicability_verified"] is False

def test_explicit_metadata_opposition_remains_a_review():
    x=audit(ref("PILKADA"))
    assert x["legal_election_type_metadata_conflict_ids"]==["DOC-7-P1"]
    assert x["legal_election_type_scope_review_ids"]==["DOC-7-P1"]
    assert "LEGAL_ELECTION_SCOPE" in x["legal_review_reason_codes"]

def test_matching_metadata_resolves_title_only_ambiguity_not_legal_currentness():
    x=audit(ref("PEMILU","Panduan Pemilihan"))
    assert x["legal_election_type_scope_review_ids"]==[]
    assert x["legal_currentness_verified"] is False

def test_missing_scope_keeps_title_conflict_for_officer():
    x=audit(ref("UNSPECIFIED"))
    assert x["legal_election_type_unresolved_title_conflict_ids"]==["DOC-7-P1"]
    assert "LEGAL_ELECTION_SCOPE" in x["legal_review_reason_codes"]

def test_review_body_preserves_explicit_metadata_input():
    x=ReviewBody(document_type="REGULATION",legal_election_type="BOTH",
                 legal_version_label="2026-1",legal_effective_date="2026-01-01")
    assert x.legal_election_type=="BOTH" and x.legal_effective_date=="2026-01-01"
