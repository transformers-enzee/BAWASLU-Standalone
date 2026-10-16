"""No-provider regression tests for worker claim and reservation safeguards."""
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.auto_relevance import reserve_automatic_ai_request, recover_stale_jobs

def test_budget_disabled_refuses_before_database_io():
    db=Mock()
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'0',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'0'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.execute.assert_not_called()

def test_sqlite_refuses_automatic_billable_reservations():
    db=Mock()
    db.bind.dialect.name='sqlite'
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'2',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.execute.assert_not_called()

def test_invalid_budget_refuses_without_database_io():
    db=Mock()
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'invalid',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.execute.assert_not_called()

def test_postgres_reservations_increment_both_quota_rows():
    db=Mock()
    db.bind.dialect.name='postgresql'
    lifetime=Mock(reserved_requests=0)
    day=Mock(reserved_requests=0)
    db.query.return_value.filter_by.return_value.with_for_update.return_value.one.side_effect=[lifetime,day]
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'2',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is True
    assert lifetime.reserved_requests==1
    assert day.reserved_requests==1
    assert db.commit.call_count==2

def test_exhausted_postgres_daily_quota_fails_closed():
    db=Mock()
    db.bind.dialect.name='postgresql'
    lifetime=Mock(reserved_requests=1)
    day=Mock(reserved_requests=2)
    db.query.return_value.filter_by.return_value.with_for_update.return_value.one.side_effect=[lifetime,day]
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'2',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is False
    assert lifetime.reserved_requests==1
    assert day.reserved_requests==2
    db.rollback.assert_called()

def test_postgres_database_failure_refuses_reservation():
    db=Mock()
    db.bind.dialect.name='postgresql'
    db.execute.side_effect=RuntimeError('simulated database failure')
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'2',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.rollback.assert_called()
