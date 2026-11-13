"""v151.0: advisory, permission-scoped officer review instructions."""
from app.assistant_grounding import audit_assistant_answer

def social(id):
    return {"record_id":id,"record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Allegation requiring context review."}
def pdf(id,status="OFFICER_REVIEWED"):
    return {"record_id":id,"record_type":"PDF_KNOWLEDGE",
            "review_status":status,"document_type":"REGULATION",
            "source_excerpt":"Pasal 21 concerns evidence verification."}
def run(items,answer,question="Review the evidence",profile="PDF_GUIDANCE"):
    return audit_assistant_answer(question,items,answer,
                                  profile=profile,language="en")
def codes(meta):
    return [x["code"] for x in meta["officer_review_steps"]]

def test_mixed_unreviewed_social_pdf_and_enforcement_steps_are_ordered_and_authorized():
    _,cited,meta=run([social("SOCIAL-1"),pdf("DOC-2-P3","UNREVIEWED")],
        "The officer must arrest the person [SOCIAL-1]. Pasal 21 explains the procedure [DOC-2-P3].")
    assert codes(meta)==[
        "VERIFY_ORIGINAL_POST_CONTEXT","REQUEST_DOCUMENT_REVIEW",
        "CONFIRM_AUTHORITY_BEFORE_ANY_ACTION"]
    assert meta["officer_review_steps"][0]["source_ids"]==["SOCIAL-1"]
    assert meta["officer_review_steps"][1]["source_ids"]==["DOC-2-P3"]
    assert meta["officer_review_steps"][2]["source_ids"]==["DOC-2-P3"]
    assert meta["legal_action_ready"] is False
    assert meta["officer_review_steps_auto_completed"] is False
    assert all(x["status"]=="NOT_STARTED" and x["officer_action_only"] for x in meta["officer_review_steps"])

def test_definitive_verdict_without_pdf_requires_official_reference_and_outcome_check():
    _,cited,meta=run([social("SOCIAL-3")],
        "The candidate is guilty [SOCIAL-3].",profile="SOCIAL_ANALYSIS")
    assert codes(meta)==[
        "VERIFY_ORIGINAL_POST_CONTEXT","LOCATE_AUTHORIZED_LEGAL_REFERENCE",
        "VERIFY_OFFICIAL_LEGAL_OUTCOME"]
    assert meta["officer_review_steps"][-1]["source_ids"]==[]
    assert meta["human_review_required"] is True

def test_legal_article_mismatch_targets_only_displayed_pdf():
    _,cited,meta=run([pdf("DOC-1-P1"),pdf("DOC-5-P4")],
        "Pasal 88 applies [DOC-1-P1].")
    assert codes(meta)==["MATCH_CITED_LEGAL_PASSAGES"]
    assert meta["officer_review_steps"][0]["source_ids"]==["DOC-1-P1"]
    assert "DOC-5-P4" not in str(meta["officer_review_steps"])

def test_excess_and_unavailable_citations_are_not_in_review_source_ids():
    items=[social(f"SOCIAL-{i}") for i in range(1,14)]
    _,cited,meta=run(items,
        "Evidence: "+" ".join(f"[SOCIAL-{i}]" for i in range(1,14))+" [SOCIAL-999]",
        profile="SOCIAL_ANALYSIS")
    assert "RECHECK_MISSING_OR_OMITTED_REFERENCES" in codes(meta)
    referenced=[sid for row in meta["officer_review_steps"] for sid in row["source_ids"]]
    assert "SOCIAL-13" not in referenced and "SOCIAL-999" not in referenced
    assert set(referenced).issubset(set(cited))
    assert meta["omitted_excess_citation_count"]==1

def test_neutral_pdf_answer_has_no_fabricated_officer_tasks():
    _,_,meta=run([pdf("DOC-9-P1")],
        "Pasal 21 describes reviewing evidence [DOC-9-P1].")
    assert meta["officer_review_steps"]==[]
    assert meta["legal_verdict_confirmed"] is False

def test_no_evidence_directive_creates_reference_and_authority_steps_without_auto_action():
    _,_,meta=run([],"The officer must prosecute immediately.",
                 profile="SOCIAL_ANALYSIS")
    assert codes(meta)==[
        "LOCATE_AUTHORIZED_LEGAL_REFERENCE","CONFIRM_AUTHORITY_BEFORE_ANY_ACTION"]
    assert all(row["source_ids"]==[] for row in meta["officer_review_steps"])
    assert meta["legal_action_ready"] is False
