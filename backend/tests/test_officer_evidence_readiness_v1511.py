"""v151.1: officer review guidance, legal reference readiness, formal evidence provenance."""
from app.assistant_grounding import audit_assistant_answer

def pdf(id):
    return {"record_id":id,"record_type":"PDF_KNOWLEDGE",
            "review_status":"OFFICER_REVIEWED","document_type":"REGULATION",
            "source_excerpt":"Pasal 5 requires evidence verification."}
def formal(id):
    return {"record_id":id,"record_type":"FORMAL_INTELLIGENCE",
            "source_excerpt":"Recorded intake, evidence and officer history."}
def social(id):
    return {"record_id":id,"record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Unverified allegation."}
def run(question,rows,answer,profile="SOCIAL_ANALYSIS"):
    return audit_assistant_answer(question,rows,answer,
                                  profile=profile,language="en")
def codes(meta):
    return [step["code"] for step in meta["officer_review_steps"]]

def test_no_evidence_legal_question_requires_officer_reference_and_review():
    _,cited,meta=run("Explain the applicable law",[],
                     "The applicable rules require careful checking.")
    assert cited==[]
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_NOT_CITED"
    assert meta["human_review_required"] is True
    assert codes(meta)==["LOCATE_AUTHORIZED_LEGAL_REFERENCE"]
    assert meta["legal_action_ready"] is False

def test_cited_social_post_does_not_pass_as_legal_pdf_reference():
    _,cited,meta=run("What legal provision applies?",[social("SOCIAL-1")],
                     "The post alleges wrongdoing [SOCIAL-1].")
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_NOT_CITED"
    assert codes(meta)==["VERIFY_ORIGINAL_POST_CONTEXT","LOCATE_AUTHORIZED_LEGAL_REFERENCE"]
    assert meta["evidence_citation_coverage_is_truth_verification"] is False

def test_formal_intelligence_requires_provenance_check_without_approval():
    _,cited,meta=run("Summarize the case",[formal("INT-92")],
                     "The intake record lists officer observations [INT-92].")
    assert cited==["INT-92"]
    assert codes(meta)==["TRACE_FORMAL_EVIDENCE_CHAIN"]
    assert meta["officer_review_steps"][0]["source_ids"]==["INT-92"]
    assert meta["officer_review_steps"][0]["status"]=="NOT_STARTED"
    assert meta["legal_action_ready"] is False

def test_mixed_social_formal_pdf_order_and_scope():
    rows=[social("SOCIAL-7"),formal("INT-5"),pdf("DOC-4-P2")]
    answer="The original post [SOCIAL-7] and intake [INT-5] are contextual. Pasal 5 is in [DOC-4-P2]."
    _,cited,meta=run("Which law applies?",rows,answer,profile="PDF_GUIDANCE")
    assert codes(meta)==["VERIFY_ORIGINAL_POST_CONTEXT","TRACE_FORMAL_EVIDENCE_CHAIN"]
    assert meta["evidence_citation_coverage"]=="LEGAL_REFERENCE_CITED_UNVERIFIED"
    all_ids=[sid for step in meta["officer_review_steps"] for sid in step["source_ids"]]
    assert set(all_ids).issubset(set(cited))

def test_uncited_selected_social_evidence_is_not_claimed_as_cited():
    _,cited,meta=run("Summarize the posts",[social("SOCIAL-7")],
                     "No source identifier appears here.")
    assert meta["evidence_citation_coverage"]=="SELECTED_EVIDENCE_NOT_CITED"
    assert meta["officer_review_steps"]==[]
    assert meta["human_review_required"] is True

def test_neutral_no_evidence_response_has_no_fabricated_officer_task():
    _,cited,meta=run("Explain the workflow",[],
                     "No relevant saved evidence is available.")
    assert meta["evidence_citation_coverage"]=="NO_CITED_EVIDENCE"
    assert meta["human_review_required"] is False
    assert meta["officer_review_steps"]==[]
