"""v171.7: missing cross-snapshot evidence is never a paid-processing preflight."""
from app.assessment_exception_review import assessment_exception_review

def triage():
    return {'status':'PENDING_WORK','buckets_partition_all_jobs':True,
      'pending_breakdown':{'breakdown_reconciled':True},
      'completion_snapshot_reconciled':True,
      'provider_usage_integrity':{'status':'NO_RECORDED_ISSUES'},
      'completion_provenance':{'completed_jobs':1,'usage_backed_completed':1,
        'requires_historical_usage_review':0,'completed_partition_reconciled':True}}

def approval():
    return {'status':'ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL',
      'manual_request_capacity_if_separately_approved':4}

def test_missing_snapshot_blocks_positive_preflight_without_rewriting_history():
    result=assessment_exception_review([],triage(),approval())
    gate=result['manual_approval_review_gate']
    assert gate['status']=='BLOCKED'
    assert 'SNAPSHOT_AUDIT_UNAVAILABLE' in gate['blockers']
    assert not gate['snapshot_audit_supplied']
    assert gate['displayable_capacity_if_all_checks_clear']==0
    assert gate['legacy_preflight_capacity']==4
    assert result['database_writes']==0 and not result['paid_provider_called']

def test_supplied_consistent_snapshot_remains_advisory_only():
    result=assessment_exception_review([],triage(),approval(),{'all_consistent':True})
    gate=result['manual_approval_review_gate']
    assert gate['status']=='PREFLIGHT_ONLY'
    assert gate['snapshot_audit_supplied']
    assert gate['displayable_capacity_if_all_checks_clear']==4
    assert gate['never_authorizes_paid_processing']

def test_explicitly_invalid_snapshot_blocks_without_false_history_proof():
    result=assessment_exception_review([],triage(),approval(),{'all_consistent':False})
    gate=result['manual_approval_review_gate']
    assert gate['status']=='BLOCKED'
    assert 'UNRECONCILED_SNAPSHOT' in gate['blockers']
    assert result['historical_provider_usage_independently_verified'] is False
