"""Safe no-provider tests for automatic request reservation."""
import os
from unittest.mock import Mock, patch
from app.auto_relevance import reserve_automatic_ai_request

def test_automatic_reservation_fail_closed_without_explicit_limits():
    db=Mock()
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'0',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'0'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.execute.assert_not_called()

def test_sqlite_auto_reservation_is_rejected():
    db=Mock()
    db.bind.dialect.name='sqlite'
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'2',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.execute.assert_not_called()

def test_invalid_limit_does_not_reserve():
    db=Mock()
    with patch.dict(os.environ,{'BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN':'invalid',
                                'BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN':'5'}):
        assert reserve_automatic_ai_request(db,1) is False
    db.execute.assert_not_called()
