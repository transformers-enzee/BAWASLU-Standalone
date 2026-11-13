"""v151.7: election-type hints and unknown legal version metadata are not approvals."""
from app.assistant_grounding import audit_assistant_answer

def page(ref,title,kind="REGULATION"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "title":title,"document_type":kind,
            "review_status":"OFFICER_REVIEWED","source_excerpt":"Pasal 21."}

def run(question,records,answer):
    return audit_assistant_answer(question,records,answer,
                                  profile="PDF_GUIDANCE",language="en")[2]

def test_pemilu_question_with_pilkada_title_flags_possible_scope_conflict():
    meta=run("Which Pemilu law applies?",[page("DOC-1-P1","Pedoman Pilkada")],
             "Pasal 21 [DOC-1-P1].")
    assert meta["legal_question_election_type_hints"]==["PEMILU"]
    assert meta["legal_election_type_title_conflict_ids"]==["DOC-1-P1"]
    assert "VERIFY_ELECTION_TYPE_APPLICABILITY" in [x["code"] for x in meta["officer_review_steps"]]
    assert meta["legal_election_type_applicability_verified"] is False

def test_matching_pemilu_title_never_certifies_applicability():
    meta=run("What does Pemilu law say?",[page("DOC-1-P1","Peraturan Pemilu")],
             "Pasal 21 [DOC-1-P1].")
    assert meta["legal_election_type_title_conflict_ids"]==[]
    assert meta["legal_election_type_applicability_verified"] is False
    assert meta["legal_document_version_verified"] is False

def test_generic_title_requires_officer_check_for_explicit_election_type():
    meta=run("Rules for Pilkada?",[page("DOC-1-P1","Pedoman Internal")],
             "Pasal 21 [DOC-1-P1].")
    assert meta["legal_election_type_title_unknown_ids"]==["DOC-1-P1"]
    assert "LEGAL_ELECTION_SCOPE" in meta["legal_review_reason_codes"]

def test_ambiguous_question_does_not_make_false_conflict():
    meta=run("Compare Pemilu and Pilkada rules",
             [page("DOC-1-P1","Pedoman Pemilu")],"Pasal 21 [DOC-1-P1].")
    assert meta["legal_question_election_type_hints"]==["PEMILU","PILKADA"]
    assert meta["legal_election_type_title_conflict_ids"]==[]

def test_nonlegal_report_cannot_be_used_for_election_scope_matching():
    meta=run("Rules for Pemilu?",[page("DOC-1-P1","Pilkada report","REPORT")],
             "The report discusses Pasal 21 [DOC-1-P1].")
    assert meta["legal_cited_title_election_type_hints"]==[]
    assert meta["legal_document_version_metadata_available"] is False
