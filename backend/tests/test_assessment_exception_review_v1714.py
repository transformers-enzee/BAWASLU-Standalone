"""v171.4 administrator exception review remains read-only and fail-closed."""
from app.assessment_exception_review import assessment_exception_review

def triage(status='NO_ACTIVE_WORK', usage_status='NO_RECORDED_ISSUES', reconciled=True):
    return {'status':status,'buckets_partition_all_jobs':reconciled,
        'pending_breakdown':{'breakdown_reconciled':reconciled},
        'completion_snapshot_reconciled':reconciled,
        'provider_usage_integrity':{'status':usage_status},
        'completion_provenance':{'completed_partition_reconciled':reconciled}}

def test_clean_queue_never_claims_external_provider_usage_verified():
    result=assessment_exception_review([],triage(),{})
    assert result['queue_exceptions_clear']
    assert result['queue_has_no_active_work']
    assert result['historical_provider_usage_independently_verified'] is False
    assert result['historical_usage_state']=='NOT_INDEPENDENTLY_VERIFIED'
    assert result['next_review_step']=='VERIFY_HISTORICAL_USAGE_INDEPENDENTLY'
    assert result['database_writes']==0 and not result['paid_provider_called']

def test_priority_and_unknown_codes_fail_closed_without_double_counting():
    issues=[{'code':'UNQUEUED_EVIDENCE','count':3},
            {'code':'USAGE_INTEGRITY_WARNING','count':5},
            {'code':'SNAPSHOT_AGGREGATE_DRIFT','count':1},
            {'code':'FUTURE_UNKNOWN_CONFLICT','count':2}]
    result=assessment_exception_review(issues,triage('HOLD_FOR_HISTORY_REVIEW'),{})
    assert result['review_order']==['SNAPSHOT','HISTORY','QUEUE']
    assert [g['active_categories'] for g in result['groups']]==[1,2,1]
    assert result['active_exception_categories']==4
    assert result['unknown_codes']==['FUTURE_UNKNOWN_CONFLICT']
    assert result['next_review_step']=='INVESTIGATE_PROVIDER_HISTORY'
    assert all(g['flag_counts_are_not_distinct_jobs'] for g in result['groups'])

def test_snapshot_drift_takes_precedence_and_missing_usage_audit_is_not_clean():
    result=assessment_exception_review([],triage(reconciled=False,usage_status='AUDIT_UNAVAILABLE'),{})
    assert result['next_review_step']=='REFRESH_SNAPSHOT'
    assert not result['snapshot_reconciled']
    assert not result['usage_audit_available']
    assert result['historical_provider_usage_independently_verified'] is False

def test_queue_reconciliation_next_without_history_exceptions():
    result=assessment_exception_review([{'code':'PENDING_ALREADY_ASSESSED','count':2}],
        triage('QUEUE_RECONCILIATION'),{})
    assert result['next_review_step']=='RECONCILE_QUEUE'
    assert not result['queue_exceptions_clear']
    assert result['historical_usage_state']=='NOT_INDEPENDENTLY_VERIFIED'
