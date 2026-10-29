"""Zero-credit source previews and unvalidated, holdout-safe V18 draft."""
from app.processing_hints import summarize_scoped_findings
from app.smart_radar_qa_tuning import calibration_draft_payload
from app.smart_radar_qa import CAT_SET

SOURCE='Warga mempertanyakan pelayanan pemilu di TPS dan ingin penjelasan BAWASLU.'

def test_source_excerpt_does_not_pretend_to_be_ai_summary():
    row={'id':'1','campaign_id':'91','text_content':SOURCE,
         'relevance_label':'RELEVANT','potential_issues':[{'evidence_quote':SOURCE}],
         'player_summaries':[]}
    processing=summarize_scoped_findings([row])
    player=processing['intelligence_players']['Potential Violations']['entries'][0]
    assert player['source_excerpt']==SOURCE
    assert player['source_excerpt_provenance']=='ORIGINAL_POST_NOT_AI_SUMMARY'
    assert player['ai_summary_draft'] is None
    assert processing['processing_diagnostics']['posts_with_saved_ai_summary_drafts']==0
    assert processing['paid_provider_called'] is False

def test_v18_candidate_prompt_has_all_seven_categories_and_no_gold_leak():
    draft=calibration_draft_payload()
    assert all(category.lower() in draft['instructions'].lower() for category in CAT_SET)
    assert 'Disputes / Legal versus Allegations / Violations' in draft['instructions']
    assert 'Election Operations versus Participatory Oversight' in draft['instructions']
    assert draft['holdout_excluded_from_draft'] is True
    assert draft['no_new_accuracy_claim'] is True
    assert draft['historical_versions_immutable'] is True
    assert draft['paid_provider_called'] is False
    assert draft['recommended_reference_mode']=='shahrin-ref-v3'

def test_workbench_requires_explicit_click_before_saving_or_running():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]/'frontend/src'
    workbench=(root/'components/QAPromptWorkbench.jsx').read_text()
    inbox=(root/'pages/Inbox.jsx').read_text()
    for needle in ("onClick={loadCalibrationDraft}",
         "calibration-draft","V18 candidate draft loaded"):
        assert needle in workbench
    assert "Saving a new immutable version is a separate action" in workbench
    assert 'Source extract (not AI summary)' in inbox
    assert 'paid_provider_called' not in "automatic model requests"
