"""Contract tests for source-scoped AI issue distribution."""
import ast
from pathlib import Path

def test_topics_are_source_grounded_and_separate():
    base=Path(__file__).resolve().parents[1]
    module=base/'app'/'issue_distribution.py'
    source=module.read_text()
    ast.parse(source)
    assert 'live_inbox_findings' in source
    assert 'REPUTATION ONLY' in source
    assert 'ELECTORAL OPERATIONS' in source
    assert 'topic_id' in source and '"others"' in source
    assert 'len(topics)!=5' in source
    assert 'len(assignments)!=len(identifiers)' in source
    assert 'response.raise_for_status()' in source

def test_no_provider_call_on_dashboard():
    base=Path(__file__).resolve().parents[1]
    radar=(base/'app'/'smart_radar.py').read_text()
    assert 'issue_distribution/analyze' not in radar
    assert 'paid_provider_called":False' in radar
