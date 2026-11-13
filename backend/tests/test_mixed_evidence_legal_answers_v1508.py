"""v150.8 mixed social/PDF legal responses: attribution, overflow and review summary."""
import re
from app.assistant_grounding import audit_assistant_answer
from app.assistant_answer_quality import evaluate_answer_quality

def pdf(id,review="OFFICER_REVIEWED"):
    return {"record_id":id,"record_type":"PDF_KNOWLEDGE",
            "review_status":review,"document_type":"REGULATION",
            "source_excerpt":"Pasal 21 concerns evidence review, not a confirmed violation."}

def social(id):
    return {"record_id":id,"record_type":"SOCIAL_LISTENING",
            "source_excerpt":"Unverified election allegation requiring officer review."}

def run(question,items,answer,profile="SOCIAL_ANALYSIS"):
    out,cited,meta=audit_assistant_answer(question,items,answer,
                                          profile=profile,language="en")
    qa=evaluate_answer_quality(question,items,out,cited,
                               profile=profile,grounding=meta)
    return out,cited,meta,qa

def test_concessive_uncertainty_does_not_hide_independent_guilt_claim():
    evidence=[social("SOCIAL-71"),pdf("DOC-7-P2")]
    sentence=("Although the allegation is unverified, the candidate is guilty. "
              "Evidence is in [SOCIAL-71] and procedure is [DOC-7-P2].")
    out,cited,meta,qa=run("Summarize the case",evidence,sentence)
    assert meta["legal_categorical_outcome_flags"]==["ASSERTED_LEGAL_GUILT"]
    assert "CATEGORICAL_LEGAL_OUTCOME" in meta["legal_review_reason_codes"]
    assert meta["legal_action_ready"] is False
    assert "Legal certainty caution" in out
    assert next(x for x in qa["checks"] if x["id"]=="legal_uncertainty")["status"]=="REVIEW_REQUIRED"

def test_indonesian_concessive_lead_does_not_hide_verdict():
    out,cited,meta,qa=run("Ringkas", [social("SOCIAL-1")],
        "Meskipun laporan belum diverifikasi, pelaku terbukti bersalah. [SOCIAL-1]")
    assert "ASSERTED_LEGAL_GUILT" in meta["legal_categorical_outcome_flags"]
    assert qa["review_required_checks"]>0

def test_reported_speech_is_not_reclassified_as_legal_verdict():
    evidence=[social("SOCIAL-71")]
    for answer in [
        "According to reports, the candidate is guilty. [SOCIAL-71]",
        "Although the claim sounds certain, it remains an allegation. [SOCIAL-71]",
        "Is the candidate guilty? [SOCIAL-71]",
    ]:
        _,_,meta,_=run("Summarize",evidence,answer)
        assert meta["legal_categorical_outcome_flags"]==[]

def test_more_than_twelve_unique_citations_are_removed_and_not_counted():
    evidence=[social(f"SOCIAL-{i}") for i in range(1,15)]
    answer="Evidence: "+" ".join(f"[SOCIAL-{i}]" for i in range(1,15))
    output,cited,meta,qa=run("What do the records show?",evidence,answer)
    assert cited==[f"SOCIAL-{i}" for i in range(1,13)]
    assert "[SOCIAL-13]" not in output and "[SOCIAL-14]" not in output
    assert "[SOCIAL-12]" in output
    assert meta["omitted_excess_citation_count"]==2
    assert meta["citation_reference_limit"]==12
    assert meta["citation_ids_valid"] is True
    assert meta["human_review_required"] is True
    assert "Citation limit caution" in output
    assert next(c for c in qa["checks"] if c["id"]=="citation_grounding")["status"]=="REVIEW_REQUIRED"
    assert set(re.findall(r"\[SOCIAL-\d+\]",output))==set(f"[SOCIAL-{i}]" for i in range(1,13))

def test_repeat_of_first_citation_still_valid_after_limit():
    evidence=[social(f"SOCIAL-{i}") for i in range(1,14)]
    answer=" ".join([f"[SOCIAL-{i}]" for i in range(1,14)]+["[SOCIAL-1]"])
    out,cited,meta,qa=run("Records",evidence,answer)
    assert out.count("[SOCIAL-1]")==2
    assert len(cited)==12
    assert meta["omitted_excess_citation_count"]==1
    assert meta["omitted_excess_citation_ids"]==["SOCIAL-13"]

def test_mixed_allegation_pdf_and_enforcement_has_distinct_review_reasons():
    evidence=[social("SOCIAL-11"),pdf("DOC-11-P1",review="UNREVIEWED")]
    ans=("A post alleges wrongdoing [SOCIAL-11]. "
         "The officer must arrest the suspect [DOC-11-P1]. "
         "This violation has been confirmed [SOCIAL-11].")
    out,cited,meta,qa=run("Review this incident",evidence,ans,profile="PDF_GUIDANCE")
    assert meta["legal_enforcement_recommendation_needs_officer_review"] is True
    assert meta["legal_categorical_outcome_needs_officer_review"] is True
    assert meta["cited_unreviewed_pdf_pages"]==1
    assert set(meta["legal_review_reason_codes"])=={
        "CATEGORICAL_LEGAL_OUTCOME","ENFORCEMENT_RECOMMENDATION","CITED_UNREVIEWED_PDF"}
    assert meta["legal_review_reason_count"]==3
    assert meta["legal_action_ready"] is False
    assert next(c for c in qa["checks"] if c["id"]=="legal_uncertainty")["status"]=="REVIEW_REQUIRED"
    assert "Source caution" in out and "Enforcement caution" in out

def test_neutral_mixed_source_answer_does_not_invent_legal_conclusion():
    evidence=[social("SOCIAL-11"),pdf("DOC-11-P1")]
    answer="The social claim needs verification [SOCIAL-11]. Pasal 21 concerns evidence review [DOC-11-P1]."
    out,cited,meta,qa=run("Explain the sources",evidence,answer,profile="PDF_GUIDANCE")
    assert meta["legal_categorical_outcome_flags"]==[]
    assert meta["legal_enforcement_directive_flags"]==[]
    assert meta["omitted_excess_citation_count"]==0
    assert meta["legal_review_reason_count"]==0
    assert meta["legal_action_ready"] is False
    assert meta["legal_verdict_confirmed"] is False
