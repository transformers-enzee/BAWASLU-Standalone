"""No-provider tests for conditional recovery of stale AI jobs."""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.auto_relevance import recover_stale_jobs

def _session(jobs, updated_rows=1):
    db=Mock()
    db.query.return_value.filter.return_value.limit.return_value.all.return_value=jobs
    db.execute.return_value.rowcount=updated_rows
    return db

def test_pending_recovery_uses_conditional_atomic_update():
    job=Mock(id=101,state='PROCESSING',attempts=1,updated_at=datetime.utcnow()-timedelta(minutes=15))
    db=_session([job])
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==1
    assert db.execute.call_args.args[0].compile().params['state']=='PENDING'
    db.commit.assert_called_once()
    db.close.assert_called_once()

def test_exhausted_retry_recovers_to_failed():
    job=Mock(id=102,state='PROCESSING',attempts=3,updated_at=datetime.utcnow()-timedelta(minutes=15))
    db=_session([job])
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==1
    assert db.execute.call_args.args[0].compile().params['state']=='FAILED'

def test_concurrent_recovery_does_not_overcount_lost_claim():
    job=Mock(id=103,state='PROCESSING',attempts=1,updated_at=datetime.utcnow()-timedelta(minutes=15))
    db=_session([job],updated_rows=0)
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==0

def test_no_stale_jobs_no_updates():
    db=_session([])
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==0
    db.execute.assert_not_called()
    db.close.assert_called_once()
