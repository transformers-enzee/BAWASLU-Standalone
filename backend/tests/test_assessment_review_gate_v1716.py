"""v171.6 consolidated administrator preflight never grants paid AI authority."""
from app.assessment_exception_review import assessment_exception_review

def triage(usage='NO_RECORDED_ISSUES', valid=True):
    return {'status':'PENDING_WORK','buckets_partition_all_jobs':valid,
      'pending_breakdown':{'breakdown_reconciled':valid},
      'completion_snapshot_reconciled':valid,
      'provider_usage_integrity':{'status':usage},
      'completion_provenance':{'completed_jobs':2,'usage_backed_completed':2,
        'requires_historical_usage_review':0,'completed_partition_reconciled':True}}

def accepted():
    return {'status':'ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL',
      'manual_request_capacity_if_separately_approved':7}

def test_clean_review_only_never_authorizes_paid_work():
    result=assessment_exception_review([],triage(),accepted(),{'all_consistent':True})
    gate=result['manual_approval_review_gate']
    assert gate['status']=='PREFLIGHT_ONLY'
    assert gate['displayable_capacity_if_all_checks_clear']==7
    assert gate['never_authorizes_paid_processing']
    assert result['paid_provider_called'] is False and result['database_writes']==0

def test_independent_snapshot_drift_overrides_positive_legacy_preflight():
    result=assessment_exception_review([],triage(),accepted(),{'all_consistent':False})
    gate=result['manual_approval_review_gate']
    assert gate['status']=='BLOCKED'
    assert 'UNRECONCILED_SNAPSHOT' in gate['blockers']
    assert gate['legacy_preflight_capacity']==7
    assert gate['displayable_capacity_if_all_checks_clear']==0

def test_missing_usage_audit_overrides_positive_legacy_preflight():
    result=assessment_exception_review([],triage('AUDIT_UNAVAILABLE'),accepted(),{'all_consistent':True})
    assert 'MISSING_DIAGNOSTIC_AUDITS' in result['manual_approval_review_gate']['blockers']
    assert result['manual_approval_review_gate']['displayable_capacity_if_all_checks_clear']==0

def test_historical_exception_and_unknown_code_never_approve():
    result=assessment_exception_review(
      [{'code':'STALE_PROCESSING','count':1},{'code':'FUTURE_UNKNOWN_CODE','count':2}],
      triage(),accepted(),{'all_consistent':True})
    blockers=result['manual_approval_review_gate']['blockers']
    assert 'HISTORICAL_EXCEPTION' in blockers
    assert 'UNRECOGNIZED_EXCEPTION' in blockers

def test_queue_exception_and_zero_capacity_fail_closed():
    result=assessment_exception_review(
      [{'code':'UNQUEUED_EVIDENCE','count':3}],triage(),
      {'status':'ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL',
       'manual_request_capacity_if_separately_approved':0},
      {'all_consistent':True})
    blockers=result['manual_approval_review_gate']['blockers']
    assert 'QUEUE_RECONCILIATION_REQUIRED' in blockers
    assert 'NO_SEPARATELY_APPROVABLE_CAPACITY' in blockers

def test_original_blocked_preflight_remains_blocked():
    result=assessment_exception_review([],triage(),
      {'status':'CONFIGURATION_OR_BUDGET_BLOCKED',
       'manual_request_capacity_if_separately_approved':7},
      {'all_consistent':True})
    gate=result['manual_approval_review_gate']
    assert 'LEGACY_PREFLIGHT_NOT_ELIGIBLE' in gate['blockers']
    assert gate['status']=='BLOCKED'
    assert gate['displayable_capacity_if_all_checks_clear']==0
