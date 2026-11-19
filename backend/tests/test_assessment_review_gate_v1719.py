"""v171.9: reject contradictory nested read-only administrator diagnostics."""
from app.assessment_exception_review import assessment_exception_review

def triage():
    return {'status':'PENDING_WORK','buckets_partition_all_jobs':True,
        'pending_breakdown':{'breakdown_reconciled':True},
        'completion_snapshot_reconciled':True,
        'provider_usage_integrity':{'status':'NO_RECORDED_ISSUES'},
        'completion_provenance':{'completed_jobs':1,'usage_backed_completed':1,
            'requires_historical_usage_review':0,'completed_partition_reconciled':True}}

def accepted():
    return {'status':'ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL',
        'manual_request_capacity_if_separately_approved':3}

def result(issues, t, snapshot=None):
    return assessment_exception_review(issues,t,accepted(),
        {'all_consistent':True,'failed_checks':[]} if snapshot is None else snapshot)

def test_consistent_diagnostics_are_advisory_and_no_provider_work_occurs():
    r=result([],triage())
    assert r['diagnostics_consistent']
    assert r['manual_approval_review_gate']['status']=='PREFLIGHT_ONLY'
    assert r['paid_provider_called'] is False and r['database_writes']==0

def test_provider_usage_review_flag_missing_from_issue_list_blocks():
    t=triage();t['provider_usage_integrity']['status']='REVIEW_REQUIRED'
    r=result([],t)
    assert r['diagnostic_conflicts']==['PROVIDER_FLAGS_MISSING_FROM_EXCEPTIONS']
    assert 'CONFLICTING_DIAGNOSTICS' in r['manual_approval_review_gate']['blockers']
    assert r['manual_approval_review_gate']['displayable_capacity_if_all_checks_clear']==0
    assert r['next_review_step']=='REFRESH_SNAPSHOT'

def test_matching_provider_warning_does_not_create_false_conflict():
    t=triage();t['provider_usage_integrity']['status']='REVIEW_REQUIRED'
    r=result([{'code':'USAGE_INTEGRITY_WARNING','count':2}],t)
    assert r['diagnostics_consistent']
    assert r['manual_approval_review_gate']['status']=='BLOCKED'
    assert 'HISTORICAL_EXCEPTION' in r['manual_approval_review_gate']['blockers']

def test_provenance_history_gap_missing_from_issues_blocks_preflight():
    t=triage();t['completion_provenance']['requires_historical_usage_review']=1
    r=result([],t)
    assert 'PROVENANCE_GAPS_MISSING_FROM_EXCEPTIONS' in r['diagnostic_conflicts']
    assert r['manual_approval_review_gate']['status']=='BLOCKED'

def test_partitions_and_queue_status_consistency_are_checked_independently():
    t=triage();t['completion_provenance']['completed_partition_reconciled']=False
    t['status']='RECHECK_INDEPENDENT_SNAPSHOTS'
    r=result([],t)
    assert 'COMPLETED_PARTITION_DRIFT' in r['diagnostic_conflicts']
    assert 'QUEUE_SNAPSHOT_RECHECK_REQUIRED' in r['diagnostic_conflicts']
    assert not r['completion_counts_reconciled']
    assert r['next_review_step']=='REFRESH_SNAPSHOT'

def test_contradictory_snapshot_flags_fail_closed():
    r=result([],triage(),{'all_consistent':True,'failed_checks':['inventory']})
    assert 'CONTRADICTORY_SNAPSHOT_REPORT' in r['diagnostic_conflicts']
    assert r['manual_approval_review_gate']['status']=='BLOCKED'
    assert r['historical_provider_usage_independently_verified'] is False
