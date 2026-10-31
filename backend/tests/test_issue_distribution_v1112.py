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

def test_optional_topic_storage_missing_does_not_crash_or_schedule_paid_ai(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app import issue_distribution
    monkeypatch.setattr(issue_distribution,'authorised',lambda db,user:{})
    monkeypatch.setattr(issue_distribution,'_records',
        lambda db,user:(_ for _ in ()).throw(AssertionError('Missing storage must not trigger source queries')))
    with Session(create_engine('sqlite:///:memory:')) as db:
        result=issue_distribution.distribution(None,user=object(),db=db)
    assert result['storage_status']=='UNAVAILABLE'
    assert result['operations'] is None and result['reputation'] is None
    assert result['source_total']==0
    assert 'No AI requests were scheduled' in result['note']
