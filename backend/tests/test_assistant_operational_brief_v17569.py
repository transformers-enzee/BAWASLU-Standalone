"""Zero-credit tests for structured officer-first answer and safe citation rendering."""
from app.assistant_officer_action_contract import (
    OFFICER_BRIEF_SCHEMA, BRIEF_FIELDS, sanitize_officer_brief,
    officer_response_mode, officer_mode_prompt, render_officer_brief,
    operational_brief_readiness, complete_officer_steps,
)
from app.assistant_orchestration import SCHEMA, _safe_output, answer_text


def proposed(**kwargs):
    row={
        "violation_type": "Dugaan intersepsi [SOCIAL-907]",
        "legal_status": "Allegation, not determined",
        "geographical_impact": "Belum ada provinsi terdampak terverifikasi",
        "electoral_nexus": "Belum terbukti berkaitan dengan Pemilu",
        "recommended_decision": "Kajian kewenangan oleh Bawaslu HQ",
        "evidence_limit": "Perlu periksa sumber asli",
    }
    return {**row, **kwargs}


def test_strict_provider_schema_requires_structured_brief():
    assert "operational_brief" in SCHEMA["required"]
    assert SCHEMA["properties"]["operational_brief"] == OFFICER_BRIEF_SCHEMA
    assert set(OFFICER_BRIEF_SCHEMA["required"]) == set(BRIEF_FIELDS)
    assert OFFICER_BRIEF_SCHEMA["additionalProperties"] is False


def test_sanitizer_strips_unauthorized_ids_but_preserves_allowed():
    obj=proposed(recommended_decision="Periksa [SOCIAL-907] dan [SOCIAL-999]")
    clean=sanitize_officer_brief(obj,{"SOCIAL-907"})
    assert clean["violation_type"]=="Dugaan intersepsi [SOCIAL-907]"
    assert "[SOCIAL-999]" not in clean["recommended_decision"]
    assert "[SOCIAL-907]" in clean["recommended_decision"]


def test_malformed_brief_defaults_to_empty_nonassertive_values():
    clean=sanitize_officer_brief({"legal_status":123},set())
    assert all(clean[k]=="" for k in BRIEF_FIELDS)


def test_safe_output_sanitizes_structured_brief_as_other_answer_sections():
    result=_safe_output({
        "cited_ids":["SOCIAL-907","SOCIAL-999"],
        "direct_answer":"Perlu verifikasi [SOCIAL-907]",
        "interpretation":"","observations":[],"next_checks":[],
        "limitations":[],"operational_brief":proposed(
            geographical_impact="Lokasi [SOCIAL-999] tidak pasti"),
    },{"SOCIAL-907"})
    assert result["cited_ids"]==["SOCIAL-907"]
    assert "[SOCIAL-999]" not in str(result["operational_brief"])


def test_rendered_brief_keeps_three_decision_sections_and_citations():
    brief=sanitize_officer_brief(proposed(),{"SOCIAL-907"})
    visible=render_officer_brief(brief,"id","DEEP","CASE_REVIEW")
    assert "1. Kategori dugaan pelanggaran" in visible
    assert "2. Dampak geografis" in visible
    assert "3. Rekomendasi keputusan" in visible
    assert "[SOCIAL-907]" in visible
    assert "Status hukum" in visible


def test_quick_brief_shows_compact_sections_not_extra_deep_analysis():
    brief=proposed()
    quick=render_officer_brief(brief,"en","EXECUTIVE","CASE_REVIEW")
    deep=render_officer_brief(brief,"en","INVESTIGATION","CASE_REVIEW")
    assert "1. Violation type" in quick
    assert "Legal status:" not in quick
    assert "Legal status:" in deep


def test_explicit_pdf_and_executive_report_exclude_operational_brief():
    for profile in ("PDF_GUIDANCE","EXECUTIVE_REPORT"):
        assert render_officer_brief(proposed(),"id","DEEP",profile)==""


def test_officer_modes_map_to_existing_depth_options():
    assert officer_response_mode("EXECUTIVE")=="QUICK_BRIEF"
    assert officer_response_mode("DEEP")=="ACTION_PLAN"
    assert officer_response_mode("INVESTIGATION")=="LEGAL_DEEP_DIVE"
    assert "Pemilu/Pilkada" in officer_mode_prompt("INVESTIGATION")


def test_structured_brief_is_in_actual_answer_text_before_citation_audit():
    reply=answer_text({
        "direct_answer":"Perlu kajian berdasarkan [SOCIAL-907].",
        "operational_brief":proposed(),
        "response_depth":"DEEP","response_profile":"CASE_REVIEW",
        "visual_report":True,"observations":[],"next_checks":[],
        "limitations":[],"interpretation":"",
    },True,"id")
    assert "2. Dampak geografis" in reply
    assert "Kajian kewenangan oleh Bawaslu HQ" in reply


def test_readiness_does_not_claim_factual_accuracy_or_officer_approval():
    assessment=operational_brief_readiness(
        proposed(),["a","b","c"],"CASE_REVIEW","DEEP")
    assert assessment["status"]=="STRUCTURE_PRESENT_UNVERIFIED"
    assert assessment["factually_verified"] is False
    assert assessment["officer_approved"] is False


def test_missing_operational_fields_or_steps_require_review():
    qa=operational_brief_readiness(
        {"recommended_decision":"Perlu review"},[],"CASE_REVIEW","DEEP")
    assert qa["status"]=="REVIEW_REQUIRED"
    assert set(qa["missing_fields"])=={"violation_type","geographical_impact"}


def test_case_review_gets_procedural_next_steps_without_fake_assignments():
    steps,filled=complete_officer_steps(
        "Jelaskan dugaan penyadapan ini", "CASE_REVIEW", [], "id")
    assert filled and len(steps)==3
    assert "konfirmasi lokasi" in steps[-1]


def test_pdf_answer_never_gets_added_officer_actions():
    steps,filled=complete_officer_steps(
        "Apa tindak lanjut menurut PDF ini?","PDF_GUIDANCE",[],"id")
    assert steps==[] and filled is False
