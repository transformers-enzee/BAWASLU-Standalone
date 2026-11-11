"""Inbox now collapses exact content automatically; manual grouping UI is retired.

Original sources and their individual audit decisions remain accessible through
source previews and protected backend records.
"""
from pathlib import Path


def test_collapsed_duplicate_ui_keeps_original_source_preview_and_officer_controls():
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    assert 'Original source provenance' in source
    assert 'Open original source' in source
    assert 'View source and assessment' in source
    assert 'campaignFlagReview' in source
    assert 'deduplicateInboxEvidence(findings)' in source


def test_inbox_does_not_request_or_save_manual_group_proposals_on_load():
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    for action in ('campaignFindingGroupsPreview','campaignFindingGroupsSave',
                   'campaignFindingGroupsList','campaignFindingGroupsReview',
                   'campaignFindingGroupSources'):
        assert action not in source
    assert 'Source-linked grouping review' not in source
    assert 'confirm_save:true' not in source
