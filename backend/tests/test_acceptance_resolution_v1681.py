"""v168.1: operational acceptance resolves only after review, not by displaying a plan."""
from app.assessment_operational_acceptance import assess_operational_acceptance,assessment_resolution_plan

def readiness():
    return {'queue_counts':{'claimable_pending_with_text':12},
        'per_run_request_limit':20,'daily_remaining':40,'lifetime_remaining':100,
        'ai_provider_configured':True,'database_supports_reservations':True,
        'ready_to_process':False}

def test_history_resolution_precedes_queue_with_specific_clearance_evidence():
    issues=[
        {'code':'PENDING_ALREADY_ASSESSED','count':70},
        {'code':'STALE_PROCESSING','count':1},
        {'code':'COMPLETION_PROVENANCE_GAP','count':10}]
    out=assess_operational_acceptance(readiness(),issues)
    plan=out['resolution_plan']
    assert out['status']=='HOLD_FOR_HISTORY_REVIEW'
    assert [row['group'] for row in plan]==['HISTORY','HISTORY','QUEUE']
    assert out['outstanding_resolution_categories']==3
    assert not out['all_exception_criteria_satisfied']
    assert plan[-1]['existing_read_only_preview_action']=='campaignAssessmentSupersededPreview'
    assert 'classification' in plan[-1]['clearance_criterion'].lower() or 'pending' in plan[-1]['clearance_criterion'].lower()
    assert plan[1]['existing_read_only_preview_action']=='campaignAssessmentInterruptedPreview'
    assert all(not x['automated_remediation_authorized'] for x in plan)
    assert out['manual_request_capacity_if_separately_approved']==0
    assert out['campaign_wide_hold_is_advisory_not_a_job_lock'] is True

def test_unknown_issue_is_safely_unresolved_and_not_ignored():
    out=assess_operational_acceptance(readiness(),[{'code':'NEW_EXCEPTION','count':2}])
    assert out['outstanding_resolution_categories']==1
    assert out['resolution_plan'][0]['group']=='HISTORY'
    assert not out['all_exception_criteria_satisfied']
    assert out['is_paid_ai_authorization'] is False
    assert not out['paid_provider_called']

def test_zero_count_is_not_an_open_exception():
    out=assess_operational_acceptance(readiness(),[{'code':'STALE_PROCESSING','count':0}])
    assert out['resolution_plan']==[]
    assert out['all_exception_criteria_satisfied']
    assert out['status']=='ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL'
    assert out['needs_explicit_manual_approval']

def test_stable_sorting_and_no_source_data_exposed():
    p=assessment_resolution_plan([{'code':'UNQUEUED_EVIDENCE','count':2},
        {'code':'USAGE_INTEGRITY_WARNING','count':1},
        {'code':'SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF','count':3}])
    assert [x['code'] for x in p]==[
        'SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF',
        'USAGE_INTEGRITY_WARNING','UNQUEUED_EVIDENCE']
    assert all('source_id' not in x and 'result_id' not in x for x in p)

def test_operational_endpoint_keeps_existing_permission_boundary():
    from pathlib import Path
    root=Path(__file__).parents[1]/'app'
    route=(root/'campaigns.py').read_text()
    panel=(Path(__file__).parents[2]/'frontend/src/components/intel/AssessmentOperationsPanel.jsx').read_text()
    assert "if action=='campaignAssessmentOperationsOverview':" in route
    fragment=route.split("if action=='campaignAssessmentOperationsOverview':",1)[1].split("if action=='campaignAIWorkerReadiness':",1)[0]
    assert 'if not campaign or not allowed(p,campaign):' in fragment
    assert 'Resolution checklist' in panel
    assert 'clearance_criterion' in panel
    assert 'No remediation is run here' in panel
