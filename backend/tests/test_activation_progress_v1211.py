"""Regression: interrupted AI workers must not silently appear to make progress."""
from datetime import datetime,timedelta
from types import SimpleNamespace
from app.activation_assessment import stale_processing_claim

def test_stale_processing_is_reportable_not_retried():
    now=datetime.utcnow()
    stale=SimpleNamespace(state='PROCESSING',updated_at=now-timedelta(minutes=11))
    healthy=SimpleNamespace(state='PROCESSING',updated_at=now-timedelta(seconds=20))
    pending=SimpleNamespace(state='PENDING',updated_at=now-timedelta(hours=1))
    assert stale_processing_claim(stale,now) is True
    assert stale_processing_claim(healthy,now) is False
    assert stale_processing_claim(pending,now) is False
    assert stale.state=='PROCESSING' # status detection never modifies the database

def test_stale_job_does_not_trigger_implicit_paid_retries():
    from pathlib import Path
    import app.activation_assessment as activation
    src=Path(activation.__file__).read_text()
    assert 'recover_stale_jobs' not in src # only an authorized resume quarantines claims
    assert 'requested_limit=1,target_result_id=rid' in src
