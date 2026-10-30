"""One-time paid sentiment backfill is disabled by default and strictly bounded.

All tests are free and never call an AI provider.
"""
import os
from unittest.mock import patch
from app import sentiment_backfill_once as job

def test_paid_worker_requires_both_exact_admin_controls():
    with patch.dict(os.environ,{},clear=True):
        assert not job.enabled()
    with patch.dict(os.environ,{'BAWASLU_SENTIMENT_BACKFILL_ENABLED':'true'},clear=True):
        assert not job.enabled()
    with patch.dict(os.environ,{'BAWASLU_SENTIMENT_BACKFILL_ENABLED':'true',
                                'BAWASLU_SENTIMENT_BACKFILL_RUN_ID':'wrong-run'},clear=True):
        assert not job.enabled()
    with patch.dict(os.environ,{'BAWASLU_SENTIMENT_BACKFILL_ENABLED':'true',
                                'BAWASLU_SENTIMENT_BACKFILL_RUN_ID':job.RUN_ID},clear=True):
        assert job.enabled()

def test_scope_is_hard_capped_to_user_authorized_campaign_snapshot():
    assert job.CAMPAIGN_ID==1
    assert job.SOURCE_ID_CEILING==463
    assert 0<job.MAX_PROVIDER_REQUESTS<=350

def test_disabled_run_cannot_call_openai_or_database():
    with patch.dict(os.environ,{},clear=True):
        assert job.run_once()=={'status':'DISABLED'}
