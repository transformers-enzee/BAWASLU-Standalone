"""No-credit officer action replay QA: content remains provisional and scoped."""
from app.assistant_officer_action_cards import (
    ACTION_ITEM_SCHEMA,OFFICER_ACTIONS_SCHEMA,ACTION_FIELDS,
    sanitize_officer_actions,format_officer_action,visible_officer_steps,
    officer_action_readiness)
from app.assistant_orchestration import SCHEMA,_safe_output
from app.assistant_response_profile import choose_response_profile,CASE_REVIEW,PDF_GUIDANCE


def action(**overrides):
    row={
       "reviewing_role":"HQ Intelligence (proposed)",
       "task":"Check the source allegation and original publication.",
       "evidence_required":"Original reporting and official investigative statement.",
       "expected_output":"Source-linked verification note for legal review.",
       "escalation_condition":"Only after a concrete election connection is evidenced.",
       "source_ids":["SOCIAL-894"],
    }
    return {**row,**overrides}


def test_schema_requires_all_action_fields_and_ids():
    assert "officer_actions" in SCHEMA["required"]
    assert SCHEMA["properties"]["officer_actions"] is OFFICER_ACTIONS_SCHEMA
    assert ACTION_ITEM_SCHEMA["additionalProperties"] is False
    assert set(ACTION_ITEM_SCHEMA["required"])==set(ACTION_FIELDS)|{"source_ids"}


def test_surveillance_only_suggests_review_and_never_assigns():
    actions=sanitize_officer_actions([action()],{"SOCIAL-894"})
    assert len(actions)==1
    assert actions[0]["approved"] is False
    assert actions[0]["assigned_officer"] is None
    assert actions[0]["draft_only"] is True
    assert actions[0]["source_ids"]==["SOCIAL-894"]
    assert "election connection" in actions[0]["escalation_condition"]


def test_non_authorized_ids_are_removed_from_both_text_and_id_list():
    row=action(task="Review [SOCIAL-894] but not [SOCIAL-999]",
               source_ids=["SOCIAL-999","SOCIAL-894","SOCIAL-894"])
    clean=sanitize_officer_actions([row],{"SOCIAL-894"})[0]
    assert "[SOCIAL-999]" not in clean["task"]
    assert "[SOCIAL-894]" in clean["task"]
    assert clean["source_ids"]==["SOCIAL-894"]


def test_bare_source_ids_cannot_circumvent_authorized_record_filter():
    row=action(task="Review SOCIAL-894 and unrelated SOCIAL-999",
               evidence_required="Compare INT-2025-000001 if within scope")
    clean=sanitize_officer_actions([row],{"SOCIAL-894"})[0]
    assert "[SOCIAL-894]" in clean["task"]
    assert "SOCIAL-999" not in clean["task"]
    assert "INT-2025-000001" not in clean["evidence_required"]


def test_source_ids_cannot_authorize_reported_court_verdicts():
    row=action(task="Check whether a court issued the reported Banjarbaru ruling.",
               reviewing_role="HQ legal review",source_ids=["INT-2025-000001"])
    selected=sanitize_officer_actions([row],{"INT-2025-000001"})[0]
    assert selected["approved"] is False
    assert selected["assigned_officer"] is None
    assert selected["source_ids"]==["INT-2025-000001"]


def test_malformed_actions_skipped_and_list_bounded():
    rows=[None,{"task":""},"bad",*([action()]*8)]
    result=sanitize_officer_actions(rows,{"SOCIAL-894"})
    assert len(result)<=4
    assert all(x["task"] for x in result)


def test_empty_source_ids_do_not_generate_fake_evidence():
    item=sanitize_officer_actions([action(source_ids=["SOCIAL-999"])],[])[0]
    assert item["source_ids"]==[]
    text=format_officer_action(item,"id")
    assert "[SOCIAL-999]" not in text
    assert "[SOCIAL-894]" not in text


def test_visible_indonesian_action_has_owner_evidence_deliverable_gate():
    item=sanitize_officer_actions([action()],{"SOCIAL-894"})[0]
    text=format_officer_action(item,"id")
    for label in ("Tim penelaah (usulan)","Tindakan",
                  "Bukti yang perlu diperiksa","Keluaran",
                  "Syarat eskalasi / penutupan"):
        assert label in text
    assert "[SOCIAL-894]" in text


def test_visible_english_action_uses_officer_language():
    item=sanitize_officer_actions([action()],{"SOCIAL-894"})[0]
    text=visible_officer_steps([item],"en")[0]
    for phrase in ("Suggested reviewing team","Expected deliverable",
                   "Escalation / closure gate"):
        assert phrase in text


def test_quality_only_checks_structure_not_event_truth():
    items=sanitize_officer_actions([action()]*3,{"SOCIAL-894"})
    qa=officer_action_readiness(items,"CASE_REVIEW","DEEP",
                                "What should BAWASLU do next?")
    assert qa["status"]=="STRUCTURE_PRESENT_UNVERIFIED"
    assert qa["factually_verified"] is False
    assert qa["legal_outcome_verified"] is False
    assert qa["assignments_created"] is False
    assert qa["officer_approval"] is False


def test_incomplete_action_fields_require_officer_review():
    items=sanitize_officer_actions([action(reviewing_role="",
                                         evidence_required="")],{"SOCIAL-894"})
    qa=officer_action_readiness(items,"CASE_REVIEW","EXECUTIVE",
                                "What should BAWASLU do next?")
    assert qa["status"]=="REVIEW_REQUIRED"
    assert any(x["field"]=="evidence_required" for x in qa["missing_fields"])


def test_no_false_failure_for_simple_social_analysis():
    qa=officer_action_readiness([],"SOCIAL_ANALYSIS","DEEP",
                               "Compare sentiment of SOCIAL-907 and SOCIAL-910.")
    assert qa["status"]=="NOT_APPLICABLE"


def test_pdf_only_mode_excludes_action_readiness():
    q="Berdasarkan dokumen PDF jelaskan prosedur penanganan."
    assert choose_response_profile(q,pdf_evidence=[{"record_id":"DOC-1-P1"}])==PDF_GUIDANCE
    assert officer_action_readiness([],"PDF_GUIDANCE","DEEP",q)["status"]=="NOT_APPLICABLE"


def test_operational_case_gets_case_review_when_pdf_is_available():
    q="Apa yang harus dilakukan Bawaslu untuk menindaklanjuti dugaan penyadapan?"
    assert choose_response_profile(q,pdf_evidence=[{"record_id":"DOC-1-P1"}])==CASE_REVIEW


def test_safe_output_persists_sanitized_actions_for_citation_audit():
    result=_safe_output({
      "cited_ids":["SOCIAL-894","SOCIAL-999"],
      "direct_answer":"Tinjau dugaan [SOCIAL-894]","interpretation":"",
      "observations":[],"next_checks":[],"limitations":[],
      "operational_brief":{},"officer_actions":[action(
        source_ids=["SOCIAL-894","SOCIAL-999"])],
    },{"SOCIAL-894"})
    assert result["cited_ids"]==["SOCIAL-894"]
    assert result["officer_actions"][0]["source_ids"]==["SOCIAL-894"]
    assert result["officer_actions"][0]["assigned_officer"] is None


def test_no_paid_ai_or_database_imports_in_action_module():
    from pathlib import Path
    import app.assistant_officer_action_cards as module
    text=Path(module.__file__).read_text()
    for forbidden in ("httpx","requests.","get_db(","db.commit(", "openai.responses"):
        assert forbidden not in text
