"""v168.0 acceptance must never confuse readiness with cost approval."""
from app.assessment_operational_acceptance import assess_operational_acceptance

def ready(**changes):
    r={'queue_counts':{'claimable_pending_with_text':8},
       'per_run_request_limit':12,'daily_remaining':15,'lifetime_remaining':60,
       'ai_provider_configured':True,'database_supports_reservations':True,
       'worker_enabled':False,'automatic_screening_enabled':False,
       'ready_to_process':False}
    r.update(changes)
    return r

def test_manual_readiness_does_not_depend_on_disabled_background_worker():
    out=assess_operational_acceptance(ready(),[])
    assert out['status']=='ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL'
    assert out['manual_request_capacity_if_separately_approved']==8
    assert out['automatic_worker_ready'] is False
    assert out['is_paid_ai_authorization'] is False and out['database_writes']==0

def test_historical_review_is_hard_hold_even_if_budget_exists():
    issues=[{'code':'STALE_PROCESSING','count':1},{'code':'PENDING_ALREADY_ASSESSED','count':70}]
    out=assess_operational_acceptance(ready(),issues)
    assert out['status']=='HOLD_FOR_HISTORY_REVIEW'
    assert out['manual_request_capacity_if_separately_approved']==0
    assert out['historical_review_codes']==['STALE_PROCESSING']
    assert out['queue_reconciliation_codes']==['PENDING_ALREADY_ASSESSED']
    assert out['automatically_retry_unknown_provider_requests'] is False

def test_queue_reconciliation_and_empty_queue_are_not_reported_as_completed():
    assert assess_operational_acceptance(ready(),[{'code':'UNQUEUED_EVIDENCE','count':3}])['status']=='HOLD_FOR_QUEUE_RECONCILIATION'
    assert assess_operational_acceptance(ready(queue_counts={'claimable_pending_with_text':0}),[])['status']=='NO_ELIGIBLE_WORK'

def test_provider_and_quota_blockers_do_not_grant_manual_approval():
    result=assess_operational_acceptance(ready(ai_provider_configured=False,
        daily_remaining=0),[])
    assert result['status']=='CONFIGURATION_OR_BUDGET_BLOCKED'
    assert result['manual_request_capacity_if_separately_approved']==0
    assert result['manual_configuration_blockers']==['PROVIDER_NOT_CONFIGURED','REQUEST_BUDGET_UNAVAILABLE']
    assert not result['paid_provider_called']

def test_batch_capacity_is_capped_at_twenty_and_not_cost_permission():
    out=assess_operational_acceptance(ready(
        queue_counts={'claimable_pending_with_text':100},
        per_run_request_limit=25,daily_remaining=100,lifetime_remaining=100),[])
    assert out['manual_request_capacity_if_separately_approved']==20
    assert out['needs_explicit_manual_approval'] is True

def test_real_endpoint_composes_only_read_only_checks():
    from pathlib import Path
    root=Path(__file__).parents[1]/'app'
    code=(root/'assessment_operations_overview.py').read_text()
    assert 'acceptance=assess_operational_acceptance(readiness,issues)' in code
    assert "'operational_acceptance':acceptance" in code
    assert "'database_writes':0" in code
