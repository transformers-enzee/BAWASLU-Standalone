"""v171.8 protects dynamic report fixture dates against calendar drift."""
from pathlib import Path

def test_monitoring_fixture_dates_are_relative_to_runtime():
    source=(Path(__file__).parent/'test_reporting_monitoring_v1482.py').read_text()
    start=source.index('def test_monitoring_opt_in_preserves_fast_casework_default_and_scoped_sources')
    end=source.index('def test_exports_include_monitoring_only_when_requested',start)
    fixture=source[start:end]
    assert 'recent_publication=(runtime_now-timedelta(hours=12))' in fixture
    assert 'post(15,published=recent_publication)' in fixture
    assert 'post(16,published=recent_publication' in fixture
    assert 'post(50,published=recent_publication' in fixture
    assert 'assert scoped["monitoring"]["published_in_period"]==2' in fixture
