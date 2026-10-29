from pathlib import Path
def test_captured_sentiment_controls():
    src=(Path(__file__).resolve().parents[2]/'frontend/src/components/intel/CampaignPanel.jsx').read_text()
    assert 'Filter captured posts by sentiment' in src
    assert 'Sort captured posts' in src
    assert 'CLASSIFIED_FIRST' in src
    assert 'visibleCapturedPosts.slice(0,40).map' in src
    assert 'Filters do not search outside the loaded set' in src
def test_filters_are_zero_credit_and_reset_per_campaign():
    src=(Path(__file__).resolve().parents[2]/'frontend/src/components/intel/CampaignPanel.jsx').read_text()
    assert "setCapturedSentimentFilter('ALL');setCapturedSentimentSort('HOTTEST')" in src
    assert 'onChange={e=>setCapturedSentimentFilter(e.target.value)}' in src
