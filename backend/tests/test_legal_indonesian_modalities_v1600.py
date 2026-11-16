"""v160.0 Indonesian legal modality warnings: lexical triage, not legal validation."""
import pytest
from app.assistant_claim_consistency import _patterns
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def assess(source,answer,kind="REGULATION",question="Apa ketentuan hukum?"):
    rows=[{"record_id":"DOC-7-P2","record_type":"PDF_KNOWLEDGE",
           "document_type":kind,"review_status":"OFFICER_REVIEWED",
           "source_excerpt":source}]
    visible,cited,audit=audit_assistant_answer(
        question,rows,answer,profile="PDF_GUIDANCE",language="id")
    result=evaluate_answer_quality(question,rows,visible,cited,
                                   profile="PDF_GUIDANCE",grounding=audit)
    return result["legal_claim_passage_consistency"],result["legal_review_summary"],result

@pytest.mark.parametrize("claim,source,action",[
    ("Petugas harus melapor.","Petugas tidak boleh melapor.","melapor"),
    ("Petugas wajib mendaftar.","Petugas tidak diperbolehkan mendaftar.","mendaftar"),
    ("Petugas harus mengunggah.","Petugas tidak diizinkan mengunggah.","mengunggah"),
    ("Petugas tidak boleh mengumumkan.","Petugas harus mengumumkan.","mengumumkan"),
    ("Petugas tidak diperbolehkan berkampanye.","Petugas wajib berkampanye.","berkampanye"),
    ("Petugas tidak diizinkan memilih.","Petugas diperbolehkan memilih.","memilih"),
    ("Petugas wajib melapor.","Petugas tidak harus melapor.","melapor"),
    ("Petugas tidak harus melapor.","Petugas wajib melapor.","melapor"),
    ("Petugas dilarang mendaftar.","Petugas boleh mendaftar.","mendaftar"),
    ("Petugas boleh mengumumkan.","Petugas dilarang mengumumkan.","mengumumkan"),
])
def test_possible_indonesian_modal_reversal_is_flagged_for_officer(claim,source,action):
    signal,summary,full=assess(source,claim+" [DOC-7-P2]")
    assert signal["status"]=="REVIEW_REQUIRED"
    assert signal["possible_reversal_count"]==1
    assert signal["possible_reversals"][0]["action"]==action
    issue=next(x for x in summary["issues"] if x["code"]=="PASSAGE_POLARITY")
    assert issue["priority"]=="P1" and issue["source_ids"]==["DOC-7-P2"]
    assert summary["priority_is_legal_severity"] is False
    assert signal["legal_applicability_verified"] is False
    assert full["semantic_entailment_verified"] is False

@pytest.mark.parametrize("phrase,polarity",[
    ("tidak boleh melapor","NEGATIVE"),
    ("tidak diperbolehkan melapor","NEGATIVE"),
    ("tidak diizinkan melapor","NEGATIVE"),
    ("tidak harus melapor","NOT_REQUIRED"),
    ("tidak wajib melapor","NOT_REQUIRED"),
    ("boleh melapor","PERMITTED"),
    ("diperbolehkan melapor","PERMITTED"),
    ("diizinkan melapor","PERMITTED"),
    ("harus melapor","POSITIVE"),
    ("wajib melapor","POSITIVE"),
])
def test_negation_is_not_split_or_reinterpreted_as_positive(phrase,polarity):
    assert set(_patterns(phrase))=={("melapor",polarity)}

def test_both_positive_and_negative_in_same_source_is_ambiguous():
    signal,_,_=assess(
        "Petugas harus melapor. Pejabat lain tidak boleh melapor.",
        "Petugas harus melapor [DOC-7-P2].")
    assert signal["possible_reversal_count"]==0
    assert signal["semantic_entailment_verified"] is False

def test_different_action_does_not_trigger_false_reversal():
    signal,_,_=assess("Petugas tidak boleh mendaftar.",
                       "Petugas harus melapor [DOC-7-P2].")
    assert signal["possible_reversal_count"]==0

def test_uncited_or_nonlegal_context_cannot_trigger_modal_warning():
    signal,_,_=assess("Petugas tidak boleh melapor.",
        "Petugas harus melapor [DOC-99-P3].")
    assert signal["possible_reversal_count"]==0
    signal,_,_=assess("Petugas tidak boleh melapor.",
        "Petugas harus melapor [DOC-7-P2].",kind="REPORT")
    assert signal["possible_reversal_count"]==0

def test_nonlegal_question_and_reproduced_speech_are_not_rulings():
    signal,_,_=assess("Petugas tidak boleh melapor.",
        "Petugas harus melapor [DOC-7-P2].",question="Ringkas dokumen")
    assert signal["status"]=="NOT_APPLICABLE"
    signal,_,_=assess("Petugas tidak boleh melapor.",
        "Menurut sumber, petugas harus melapor [DOC-7-P2].")
    assert signal["possible_reversal_count"]==0

def test_exact_matching_legal_phrase_is_not_officer_approval():
    signal,summary,full=assess("Petugas harus melapor.",
        "Petugas harus melapor [DOC-7-P2].")
    assert signal["status"]=="NOT_APPLICABLE"
    assert summary["automated_legal_approval"] is False
    assert full["claim_truth_verified"] is False
