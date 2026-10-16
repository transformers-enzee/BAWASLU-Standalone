"""No-provider job recovery tests. These tests do not touch a live database."""
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.auto_relevance import recover_stale_jobs

def _mock_session(jobs):
    db=Mock()
    db.query.return_value.filter.return_value.limit.return_value.all.return_value=jobs
    return db

def test_recovery_returns_stale_job_to_pending():
    job=Mock(state='PROCESSING',attempts=1,updated_at=datetime.utcnow()-timedelta(minutes=15))
    db=_mock_session([job])
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==1
    assert job.state=='PENDING'
    assert job.last_error=='Recovered stale processing job'
    db.commit.assert_called_once()
    db.close.assert_called_once()

def test_recovery_respects_maximum_attempts():
    job=Mock(state='PROCESSING',attempts=3,updated_at=datetime.utcnow()-timedelta(minutes=15))
    db=_mock_session([job])
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==1
    assert job.state=='FAILED'

def test_recovery_is_noop_without_stale_jobs():
    db=_mock_session([])
    with patch('app.auto_relevance.SessionLocal',return_value=db):
        assert recover_stale_jobs()==0
    db.commit.assert_called_once()
    db.close.assert_called_once()
