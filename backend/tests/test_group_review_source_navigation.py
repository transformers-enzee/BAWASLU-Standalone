from pathlib import Path

def test_grouping_review_links_to_original_inbox_sources():
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    assert 'Inspect source {id}' in source
    assert 'setSelected(source)' in source
    assert 'currently loaded Inbox findings' in source
    assert 'No saved review groups yet' in source

def test_grouping_review_maintains_persistent_officer_actions():
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    for action in ('campaignFindingGroupsPreview','campaignFindingGroupsSave',
                   'campaignFindingGroupsList','campaignFindingGroupsReview'):
        assert action in source
    assert 'confirm_save:true' in source
