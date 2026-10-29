"""Real closure-path changes; no inference, source migration, or UI changes."""
from app.smart_radar_qa_tuning import calibration_draft_payload
from app.auto_relevance import RELEVANCE_SCREENING_INSTRUCTIONS
from app.smart_radar_qa_tuning import exemplar_audit_status,run_exemplar_audit
import inspect

def test_12_production_ai_prompt_requests_quote_anchored_summary_in_existing_call():
    assert 'part of the SAME assessment JSON' in RELEVANCE_SCREENING_INSTRUCTIONS
    assert '1 or 2 brief neutral player_summaries' in RELEVANCE_SCREENING_INSTRUCTIONS
    assert 'Return [] when the post is irrelevant' in RELEVANCE_SCREENING_INSTRUCTIONS

def test_14_v18_has_real_audit_execution_path_with_opt_in_gates():
    source=inspect.getsource(run_exemplar_audit)
    assert 'not in (17,18)' in source
    assert 'BAWASLU_QA_V2_PAID_TEST_APPROVED' in source
    assert 'qa-exemplar-audit' in inspect.getsource(exemplar_audit_status)
    payload=calibration_draft_payload()
    assert 'Disputes / Legal' in payload['instructions']
    assert payload['no_new_accuracy_claim'] is True
