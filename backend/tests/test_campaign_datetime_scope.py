"""Regression: campaign readiness must not shadow module datetime."""
from pathlib import Path

def test_campaign_action_no_local_datetime_import():
    source=(Path(__file__).resolve().parents[1]/'app'/'campaigns.py').read_text()
    assert 'from datetime import date, datetime, timezone' in source
    assert '        from datetime import datetime' not in source
