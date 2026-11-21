"""Offline regressions for officer action copy and legal evidence scope.

This suite is deterministic and uses no database access, AI provider or writes.
"""
from app.assistant_officer_action_cards import sanitize_officer_actions
from app.assistant_orchestration import SYSTEM


def _action(evidence_required):
    return {
        "reviewing_role": "Tim kajian hukum",
        "task": "Periksa dokumen resmi terlebih dahulu.",
        "evidence_required": evidence_required,
        "expected_output": "Matriks verifikasi sumber.",
        "escalation_condition": "Eskalasi hanya dengan kewenangan yang jelas.",
        "source_ids": ["SOCIAL-740", "SOCIAL-999"],
    }


def test_removed_unavailable_citations_leave_clean_sentences():
    actions=sanitize_officer_actions(
        [_action("Salinan putusan, unggahan asli [SOCIAL-999], [SOCIAL-888], dan [SOCIAL-777].")],
        {"SOCIAL-740"})
    assert len(actions)==1
    assert actions[0]["evidence_required"]=="Salinan putusan, unggahan asli."
    assert actions[0]["source_ids"]==["SOCIAL-740"]
    assert actions[0]["draft_only"] is True
    assert actions[0]["approved"] is False


def test_dangling_connector_does_not_survive_source_removal():
    actions=sanitize_officer_actions(
        [_action("Dokumen putusan yang dikutip dalam [SOCIAL-999] serta [SOCIAL-777].")],
        {"SOCIAL-740"})
    assert actions[0]["evidence_required"]=="Dokumen putusan yang dikutip."


def test_authorized_citation_in_prose_is_preserved():
    actions=sanitize_officer_actions(
        [_action("Bandingkan [SOCIAL-740] dengan dokumen resmi.")],
        {"SOCIAL-740"})
    assert "[SOCIAL-740]" in actions[0]["evidence_required"]
    assert "[SOCIAL-999]" not in str(actions)


def test_system_requires_scope_specific_absence_and_social_attribution():
    assert "NOT 'no official ruling or BAWASLU case exists anywhere'" in SYSTEM
    assert "do not promote an unverified social citation to legal authority" in SYSTEM
    assert "put evidence IDs only in source_ids" in SYSTEM
