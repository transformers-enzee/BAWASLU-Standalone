"""No paid AI calls: officer-first prompts, scope and procedural safeguards."""
from app.assistant_response_profile import (
    choose_response_profile, PDF_GUIDANCE, CASE_REVIEW, SOCIAL_ANALYSIS)
from app.assistant_officer_action_contract import (
    officer_action_intent, complete_officer_steps, OFFICER_DECISION_CONTRACT)
from app import assistant_orchestration
from pathlib import Path

def test_case_action_question_never_auto_routes_to_pdf_only():
    q="Apa yang harus dilakukan Bawaslu atas dugaan penyadapan komunikasi?"
    assert choose_response_profile(q,pdf_evidence=[{"record_id":"DOC-1-P2"}])==CASE_REVIEW
    assert officer_action_intent(q)

def test_followup_action_is_not_pdf_only_without_document_request():
    assert choose_response_profile(
        "Bagaimana tindak lanjut Bawaslu?",pdf_evidence=[{"record_id":"DOC-2-P1"}])==CASE_REVIEW

def test_explicit_pdf_reference_stays_pdf_grounded():
    assert choose_response_profile(
        "Berdasarkan dokumen PDF, jelaskan prosedur penanganan secara rinci.",
        pdf_evidence=[{"record_id":"DOC-1-P2"}])==PDF_GUIDANCE

def test_social_comparison_stays_social_even_with_pdf_available():
    assert choose_response_profile(
        "Bandingkan sentimen unggahan SOCIAL-907 dan SOCIAL-910",
        pdf_evidence=[{"record_id":"DOC-1-P2"}])==SOCIAL_ANALYSIS

def test_officer_steps_dont_just_say_monitor():
    steps,filled=complete_officer_steps(
        "What should BAWASLU do next?",CASE_REVIEW,[],"en")
    assert filled and len(steps)==3
    assert "Legal/jurisdiction officer" in steps[1]
    assert "incident location" in steps[2]
    assert "verification note" in steps[0]

def test_preserve_three_specific_model_steps_without_padding():
    steps=["Verifikasi sumber","Telaah hukum","Rujuk dengan persetujuan"]
    assert complete_officer_steps(
        "Apa tindak lanjut Bawaslu?",CASE_REVIEW,steps,"id")==(steps,False)

def test_no_automatic_steps_for_simple_questions_or_pdf_only():
    assert complete_officer_steps("Berapa unggahan?",SOCIAL_ANALYSIS,[],"id")==([],False)
    assert complete_officer_steps("Apa tindak lanjut dalam PDF?",PDF_GUIDANCE,[],"id")==([],False)

def test_officer_contract_has_actual_operational_requirements():
    for phrase in ("VIOLATION TYPE","GEOGRAPHICAL IMPACT","PRIORITIZED NEXT ACTIONS","EXPECTED", "not the sole", "officer review"):
        assert phrase.lower() in OFFICER_DECISION_CONTRACT.lower()

def test_generator_keeps_three_visible_social_actions():
    source=Path(assistant_orchestration.__file__).read_text()
    assert '[:3] if social_brief' in source
    assert "complete_officer_steps(" in source
    assert "officer_scope or {}" in source

def test_named_social_ids_do_not_promote_unrelated_formal_records():
    source=(Path(__file__).resolve().parents[1]/"app"/"main.py").read_text()
    assert "if explicit_social_ids and not explicit_formal_ids:" in source
    assert "selected_formal=[]" in source
