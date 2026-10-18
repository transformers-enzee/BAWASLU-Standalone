"""Build 73.2: credit-free human review authorization regression tests."""
import json
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from app.issue_signals import validated_issue_signals

def test_legacy_validated_flag_eligible_for_review():
    text='Warga melaporkan dugaan pembagian uang kepada pemilih.'
    raw=json.loads('[{"category_id":7,"evidence_quote":"pembagian uang kepada pemilih"}]')
    valid=validated_issue_signals(raw,{7:'Politik Uang'},text)
    assert len(valid)==1
    assert valid[0]['requires_human_verification'] is True
    assert valid[0]['signal_provenance']=='LEGACY_MISSING_TYPE'

def test_review_must_not_use_category_id_alone():
    text='Diskusi kebijakan publik dan proses pemilu.'
    invalid=[{'category_id':7,'signal_type':'TOPIC','evidence_quote':'proses pemilu'},
             {'category_id':7,'evidence_quote':'pembagian uang kepada pemilih'}]
    assert validated_issue_signals(invalid,{7:'Politik Uang'},text)==[]

def test_inactive_category_not_reviewable():
    source='Warga melaporkan dugaan pembagian uang kepada pemilih.'
    raw=[{'category_id':7,'evidence_quote':'pembagian uang kepada pemilih'}]
    assert validated_issue_signals(raw,{},source)==[]
