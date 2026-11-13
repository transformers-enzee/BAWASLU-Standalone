"""v152.3 legal answer relevance is lexical and cannot confer legal approval."""
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def page(ref,kind="REGULATION",body="Riau election finance reporting.",title="Regulation"):
    return {"record_id":ref,"record_type":"PDF_KNOWLEDGE",
            "document_type":kind,"title":title,"source_excerpt":body,
            "review_status":"OFFICER_REVIEWED","legal_election_type":"BOTH"}

def run(question,evidence,answer):
    text,cited,ground=audit_assistant_answer(
        question,evidence,answer,profile="PDF_GUIDANCE",language="en")
    qa=evaluate_answer_quality(question,evidence,text,cited,
                               profile="PDF_GUIDANCE",grounding=ground)
    return ground,qa["legal_source_alignment"],qa

def test_unrelated_legal_page_is_flagged_even_with_valid_citation():
    _,r,qa=run("Which law governs Riau bribery?",
               [page("DOC-1-P1",body="National voter registration procedures.")],
               "This regulation mentions registration [DOC-1-P1].")
    assert r["status"]=="REVIEW_REQUIRED"
    assert "riau" in r["missing_terms"] and "bribery" in r["missing_terms"]
    assert qa["claim_truth_verified"] is False

def test_report_with_matching_terms_cannot_rescue_unrelated_legal_page():
    _,r,_=run("Which law governs Riau bribery?",
              [page("DOC-1-P1",body="Unrelated rules."),
               page("DOC-2-P1",kind="REPORT",body="Riau bribery allegations.")],
              "Context [DOC-2-P1]. Regulation [DOC-1-P1].")
    assert r["status"]=="REVIEW_REQUIRED"
    assert r["cited_legal_pages"]==1
    assert "bribery" in r["missing_terms"]

def test_uncited_eligible_document_cannot_substitute_for_cited_report():
    _,r,_=run("Which law governs Riau bribery?",
              [page("DOC-1-P1",body="Riau bribery."),
               page("DOC-2-P1",kind="REPORT",body="Riau bribery.")],
              "Internal report [DOC-2-P1].")
    assert r["status"]=="REVIEW_REQUIRED"
    assert r["cited_legal_pages"]==0

def test_relevant_overlap_still_never_means_legal_applicability_verified():
    ground,r,qa=run("Which law governs Riau bribery?",
                      [page("DOC-1-P1",body="Riau bribery reporting.")],
                      "Potential concern [DOC-1-P1].")
    assert r["status"]=="PASS"
    assert r["lexical_only"] is True
    assert r["legal_applicability_verified"] is False
    assert ground["legal_currentness_verified"] is False
    assert qa["human_accuracy"] is None

def test_generic_article_question_is_unknown_not_false_relevance_pass():
    _,r,_=run("What does Pasal 21 say?",
              [page("DOC-1-P1",body="Pasal 21 covers reporting.")],
              "Pasal 21 [DOC-1-P1].")
    assert r["status"]=="NOT_APPLICABLE"
    assert r["focus_terms"]==[]

def test_explicit_scope_conflict_overrides_lexical_overlap():
    row=page("DOC-1-P1",body="Riau bribery.")
    row["legal_election_type"]="PILKADA"
    _,r,_=run("Which Pemilu law addresses Riau bribery?",[row],
              "Pasal 21 [DOC-1-P1].")
    assert r["status"]=="REVIEW_REQUIRED"
    assert r["scope_review_ids"]==["DOC-1-P1"]

def test_social_only_question_does_not_generate_legal_relevance_warning():
    row={"record_id":"SOCIAL-1","record_type":"SOCIAL_LISTENING",
         "source_excerpt":"Riau campaign discussion"}
    _,r,_=run("Summarize Riau social discussion",[row],
              "Discussion [SOCIAL-1].")
    assert r["status"]=="NOT_APPLICABLE"

def test_question_request_verbs_do_not_create_false_missing_topic():
    _,r,_=run("Which law governs Riau bribery?",
              [page("DOC-3-P2",body="Riau bribery monitoring.")],
              "Relevant excerpt [DOC-3-P2].")
    assert r["status"]=="PASS"
    assert r["missing_terms"]==[]

def test_indonesian_topic_mismatch_requires_officer_check():
    _,r,_=run("Peraturan tentang politik uang di Riau?",
              [page("DOC-3-P2",body="Pedoman pendaftaran pemilih nasional.")],
              "Dokumen [DOC-3-P2].")
    assert r["status"]=="REVIEW_REQUIRED"
    assert "riau" in r["missing_terms"]
