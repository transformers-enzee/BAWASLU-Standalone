"""Deterministic, read-only preflight acceptance for assessment operations.

This is an advisory decision only. No result grants permission to invoke AI.
Pending manual work and unattended worker readiness are kept separate.
"""
_HISTORICAL=('STALE_PROCESSING','INTERRUPTED_HISTORY_REVIEW',
    'COMPLETION_PROVENANCE_GAP','SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF',
    'COMPLETED_LATEST_CLASSIFICATION_REVIEW','CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT',
    'USAGE_INTEGRITY_WARNING','SUPERSEDED_CLASSIFICATION_CHANGED')
_QUEUE=('UNQUEUED_EVIDENCE','PENDING_ALREADY_ASSESSED','INVENTORY_RECONCILIATION_WARNING')

def assess_operational_acceptance(readiness, issues):
    codes={str(i['code']) for i in issues if int(i.get('count',0))>0}
    claimable=max(0,int(readiness['queue_counts']['claimable_pending_with_text']))
    available=min(claimable,max(0,int(readiness['per_run_request_limit'])),
                  max(0,int(readiness['daily_remaining'])),
                  max(0,int(readiness['lifetime_remaining'])),20)
    # Manual batches require a provider and Postgres quota reservation, NOT
    # the background worker or automatic-screening switches.
    blockers=[]
    if not readiness['ai_provider_configured']:blockers.append('PROVIDER_NOT_CONFIGURED')
    if not readiness['database_supports_reservations']:blockers.append('QUOTA_RESERVATION_UNAVAILABLE')
    if not readiness['per_run_request_limit']:blockers.append('PER_RUN_CAP_ZERO')
    if not readiness['daily_remaining'] or not readiness['lifetime_remaining']:
        blockers.append('REQUEST_BUDGET_UNAVAILABLE')
    status=('HOLD_FOR_HISTORY_REVIEW' if codes.intersection(_HISTORICAL)
        else 'HOLD_FOR_QUEUE_RECONCILIATION' if codes.intersection(_QUEUE)
        else 'NO_ELIGIBLE_WORK' if not claimable
        else 'CONFIGURATION_OR_BUDGET_BLOCKED' if blockers
        else 'ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL')
    return {
        'status':status,
        'historical_review_codes':sorted(codes.intersection(_HISTORICAL)),
        'queue_reconciliation_codes':sorted(codes.intersection(_QUEUE)),
        'manual_configuration_blockers':blockers,
        'eligible_unassessed_jobs':claimable,
        'manual_request_capacity_if_separately_approved':available if not blockers and status=='ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL' else 0,
        'automatic_worker_ready':bool(readiness['ready_to_process']) and not bool(codes),
        'read_only_preflight':True,
        'is_paid_ai_authorization':False,
        'needs_explicit_manual_approval':True,
        'automatically_retry_unknown_provider_requests':False,
        'database_writes':0,
        'paid_provider_called':False,
    }
