"""v171.5: administrator exception review audit-availability and snapshot gates."""
from app.assessment_exception_review import assessment_exception_review

def snapshot(consistent=True):
    return {'all_consistent':consistent,'failed_checks':[] if consistent else ['coverage_delta']}

def triage(usage_status='NO_RECORDED_ISSUES', valid=True, completion=True):
    result={'status':'NO_ACTIVE_WORK','buckets_partition_all_jobs':valid,
        'pending_breakdown':{'breakdown_reconciled':valid},
        'completion_snapshot_reconciled':valid,
        'provider_usage_integrity':{'status':usage_status}}
    if completion:
        result['completion_provenance']={
            'completed_jobs':2,'usage_backed_completed':2,
            'requires_historical_usage_review':0,
            'completed_partition_reconciled':True}
    return result

def test_non_atomic_coverage_drift_forces_refresh_even_with_clean_queue():
    result=assessment_exception_review([],triage(),{},snapshot(False))
    assert result['next_review_step']=='REFRESH_SNAPSHOT'
    assert not result['snapshot_reconciled']
    assert result['queue_exceptions_clear']
    assert not result['historical_provider_usage_independently_verified']

def test_missing_provider_integrity_audit_is_not_clearance():
    result=assessment_exception_review([],triage('AUDIT_UNAVAILABLE'),{},snapshot())
    assert result['missing_audits']==['PROVIDER_USAGE_INTEGRITY']
    assert result['history_verification_blocked_by_missing_audits']
    assert result['historical_usage_state']=='AUDIT_UNAVAILABLE'
    assert result['next_review_step']=='RESTORE_MISSING_AUDITS'
    assert not result['historical_provider_usage_independently_verified']

def test_missing_completion_audit_requires_recovery():
    result=assessment_exception_review([],triage(completion=False),{},snapshot())
    assert result['missing_audits']==['COMPLETION_PROVENANCE']
    assert result['next_review_step']=='RESTORE_MISSING_AUDITS'
    assert not result['completion_audit_available']

def test_history_exceptions_do_not_hide_missing_audit():
    issues=[{'code':'STALE_PROCESSING','count':1}]
    result=assessment_exception_review(issues,triage('AUDIT_UNAVAILABLE'),{},snapshot())
    assert result['next_review_step']=='RESTORE_MISSING_AUDITS'
    assert result['groups'][1]['active_categories']==1
    assert result['historical_usage_state']=='AUDIT_UNAVAILABLE'

def test_duplicate_issue_codes_merge_category_but_preserve_flag_count():
    issues=[{'code':'UNQUEUED_EVIDENCE','count':2},
            {'code':'UNQUEUED_EVIDENCE','count':3},
            {'code':'NEW_UNRECOGNIZED_CONFLICT','count':1}]
    result=assessment_exception_review(issues,triage(),{},snapshot())
    queue=result['groups'][2]
    assert queue['active_categories']==1
    assert queue['exceptions'][0]['flag_count']==5
    assert result['unknown_codes']==['NEW_UNRECOGNIZED_CONFLICT']
    assert result['active_exception_categories']==2
    assert result['next_review_step']=='INVESTIGATE_PROVIDER_HISTORY'

def test_all_clean_does_not_claim_independently_verified_provider_billing():
    result=assessment_exception_review([],triage(),{},snapshot())
    assert result['next_review_step']=='VERIFY_HISTORICAL_USAGE_INDEPENDENTLY'
    assert result['historical_usage_state']=='NOT_INDEPENDENTLY_VERIFIED'
    assert result['database_writes']==0
    assert result['paid_provider_called'] is False
    assert not result['automatic_paid_ai_authorized']
