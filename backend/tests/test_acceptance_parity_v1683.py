"""v168.3 snapshot reconciliation and explicit dry-run preview contract."""
from app.assessment_snapshot_consistency import assessment_snapshot_consistency
from app.assessment_operational_acceptance import assess_operational_acceptance,assessment_resolution_plan

def samples():
    q={'ordinary_jobs':8,'pending':3,'processing':1,'completed':3,
       'failed':1,'superseded_assessed':0}
    return ({'queue_counts':q},{
        'ordinary_jobs':8,'pending_jobs':3,'processing_jobs':1,
        'completed_jobs':3,'failed_jobs':1,'superseded_assessed_jobs':0,
        'counts_reconciled':True},{
        'total_ordinary_jobs':8,'pending_jobs':3,'processing_not_stale':1,
        'completed_jobs':3,'other_failed_jobs':1,'superseded_assessed_jobs':0},
        {'superseded_assessed_jobs':0})

def test_parity_healthy_and_no_extra_queries():
    result=assessment_snapshot_consistency(*samples())
    assert result['all_consistent']
    assert not result['failed_checks']
    assert result['database_writes']==0
    assert result['new_database_queries']==0

def test_stale_independent_aggregates_are_flagged_not_called_corruption():
    a,b,c,d=samples()
    c['completed_jobs']=4
    d['superseded_assessed_jobs']=1
    result=assessment_snapshot_consistency(a,b,c,d)
    assert result['failed_checks']==['superseded_count_alignment','worker_vs_interrupted_per_state']
    assert result['recheck_required']
    assert result['database_corruption_proven'] is False

def test_completed_count_drift_is_a_history_hold():
    a,b,c,d=samples()
    b['completed_jobs']=4
    drift=assessment_snapshot_consistency(a,b,c,d)
    assert not drift['all_consistent']
    readiness={'queue_counts':{'claimable_pending_with_text':2},
        'per_run_request_limit':10,'daily_remaining':20,'lifetime_remaining':60,
        'ai_provider_configured':True,'database_supports_reservations':True,
        'ready_to_process':False}
    out=assess_operational_acceptance(readiness,[{'code':'SNAPSHOT_AGGREGATE_DRIFT','count':1}])
    assert out['status']=='HOLD_FOR_HISTORY_REVIEW'
    assert out['manual_request_capacity_if_separately_approved']==0

def test_unqueued_preview_explicit_dry_run_required():
    item=assessment_resolution_plan([{'code':'UNQUEUED_EVIDENCE','count':3}])[0]
    assert item['existing_read_only_preview_action']=='campaignAssessmentJobReconcile'
    assert item['read_only_preview_payload']=={'dry_run':True}
    assert item['preview_action_is_not_implicitly_read_only']
    from pathlib import Path
    routes=(Path(__file__).parents[1]/'app'/'campaigns.py').read_text()
    assert "if (data or {}).get('dry_run') is True:" in routes
    assert 'created=enqueue_campaign_evidence(campaign.id)' in routes

def test_unrelated_preview_actions_do_not_inherit_dry_run_flag():
    plan=assessment_resolution_plan([{'code':'PENDING_ALREADY_ASSESSED','count':4}])
    assert plan[0]['read_only_preview_payload']=={}
    assert not plan[0]['preview_action_is_not_implicitly_read_only']
