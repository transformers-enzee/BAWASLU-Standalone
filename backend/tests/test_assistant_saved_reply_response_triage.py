"""No-credit saved-reply response quality; no unscoped history reads."""
import json
from app.assistant_saved_reply_response_triage import (
    summarize_authorized_saved_reply_audit as summarize,
    summarize_authorized_saved_reply_batch as summarize_batch,
)


def synthetic_audit():
    return {
        "checks":[
            {"id":"citation_grounding","status":"REVIEW_REQUIRED",
             "reason":"Sensitive original answer that must not leak"},
            {"id":"source_relevance","status":"PASS"},
            {"id":"legal_uncertainty","status":"NOT_APPLICABLE"},
            {"id":"cross_module_consistency","status":"PASS"},
        ],
        "missing_cited_source_kinds":["PDF_KNOWLEDGE"],
        "rejected_unavailable_citation_count":1,
        "issue_triage":{
            "issue_candidate_count":2,
            "issue_category_counts":{"CITATION_INTEGRITY":2},
        },
        "raw_answer":"Confidential candidate conversation text",
        "source_excerpt":"Confidential source passage",
    }


def test_flags_and_counts_are_redacted():
    result=summarize(synthetic_audit())
    assert result["status"]=="REVIEW_FLAGS_PRESENT"
    assert result["readiness_review_ids"]==["citation_grounding"]
    assert result["missing_cited_source_kinds"]==["PDF_KNOWLEDGE"]
    assert result["rejected_citation_count"]==1
    assert result["issue_candidate_count"]==2
    text=json.dumps(result)
    assert "Confidential" not in text
    assert "Sensitive original" not in text
    assert "raw_answer" not in text
    assert "source_excerpt" not in text


def test_no_flags_never_represents_accuracy_or_approval():
    result=summarize({
        "checks":[{"id":"citation_grounding","status":"PASS"}],
        "issue_triage":{"issue_candidate_count":0},
    })
    assert result["status"]=="NO_DETERMINISTIC_FLAGS"
    assert result["no_flags_is_not_a_quality_pass"] is True
    assert result["reference_answer_comparison_performed"] is False
    assert result["factual_accuracy_verified"] is False
    assert result["human_acceptance"] is None
    assert result["original_model_output_provenance_verified"] is False
    assert result["model_calls"]==0


def test_arbitrary_reason_and_id_strings_are_not_exported():
    result=summarize({"checks":[{
        "id":"case title confidential",
        "status":"REVIEW_REQUIRED",
        "reason":"source excerpt confidential"}]})
    assert "case title" not in json.dumps(result)
    assert "source excerpt" not in json.dumps(result)
    assert result["readiness_check_counts"]["REVIEW_REQUIRED"]==1


def test_unknown_source_kinds_are_not_returned():
    result=summarize({"missing_cited_source_kinds":[
        "DOC-UNAUTHORIZED-PASSAGE","PDF_KNOWLEDGE","PDF_KNOWLEDGE",
        "OTHER_PRIVATE_LABEL"]})
    assert result["missing_cited_source_kinds"]==["PDF_KNOWLEDGE"]


def test_invalid_numeric_fields_never_become_scores():
    result=summarize({
        "rejected_unavailable_citation_count":True,
        "issue_triage":{"issue_candidate_count":-4,
                        "issue_category_counts":{"WRONG":True,"KNOWN":2}}
    })
    assert result["issue_candidate_count"]==0
    assert result["rejected_citation_count"]==0
    assert result["issue_category_count"]==1
    assert result["factual_accuracy_verified"] is False


def test_single_and_batch_routes_use_same_redacted_builder():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/
            "app"/"assistant_saved_history_eval.py").read_text(encoding="utf-8")
    assert source.count("summarize_authorized_saved_reply_audit(result)") == 2
    assert "response_quality_triage" in source
    assert "AssistantThread.user_id==user.id" in source
    assert "AssistantThread.user_id==user_id" in source



def test_batch_summary_counts_only_authorized_audited_items():
    rows=[
        {"status":"AUDITED","response_quality_triage":{
            "status":"REVIEW_FLAGS_PRESENT",
            "readiness_review_ids":["citation_grounding"]}},
        {"status":"AUDITED","response_quality_triage":{
            "status":"NO_DETERMINISTIC_FLAGS"}},
        {"status":"SOURCE_UNAVAILABLE","response_quality_triage":{
            "status":"NO_DETERMINISTIC_FLAGS"}},
        {"status":"INELIGIBLE"},
    ]
    result=summarize_batch(rows)
    assert result["audited_with_review_flags"]==1
    assert result["audited_without_detected_flags"]==1
    assert result["unassessed_or_unavailable"]==2
    assert result["core_review_reason_occurrences"]=={"citation_grounding":1}
    assert result["human_accuracy"] is None
    assert result["paid_ai_calls"]==0


def test_batch_missing_triage_is_never_counted_as_accurate():
    result=summarize_batch([
        {"status":"AUDITED"},
        {"status":"AUDITED","response_quality_triage":{"status":"UNKNOWN"}},
        {"status":"AUDITED","response_quality_triage":{
            "status":"REVIEW_FLAGS_PRESENT","readiness_review_ids":[
                "SECRET CONTENT","legal_uncertainty"]}},
    ])
    assert result["audited_without_detected_flags"]==0
    assert result["unassessed_or_unavailable"]==2
    assert result["audited_with_review_flags"]==1
    assert result["core_review_reason_occurrences"]=={"legal_uncertainty":1}
    assert "SECRET CONTENT" not in json.dumps(result)
    assert result["no_flags_is_not_a_quality_pass"] is True


def test_saved_history_batch_route_returns_aggregate_builder():
    from pathlib import Path
    text=(Path(__file__).resolve().parents[1]/
          "app"/"assistant_saved_history_eval.py").read_text(encoding="utf-8")
    assert '"response_quality_batch_triage":summarize_authorized_saved_reply_batch(output)' in text
    assert "AssistantThread.user_id==user_id" in text
    assert "resolve_mixed_audit_sources(db,batch_principal,audit)" in text
