"""v170.3 no-cost administrator triage of assessment queue lifecycle.

Pure presentation logic over existing campaign-scoped aggregate snapshots.
No source identifiers, raw errors, worker dispatch, or database access.
"""
_BUCKETS=(
    ('STALE_PROCESSING','stale_processing_jobs','URGENT_HISTORY_REVIEW',
     'Inspect provider history and billing before explicitly confirmed quarantine.'),
    ('QUARANTINED_INTERRUPTED','already_quarantined_for_manual_review','HISTORY_REVIEW',
     'Verify prior provider result and usage; do not automatically retry.'),
    ('FAILED_OTHER','other_failed_jobs','HISTORY_REVIEW',
     'Review failure history and eligibility before separately authorizing any new request.'),
    ('SUPERSEDED_ASSESSED','superseded_assessed_jobs','NO_RETRY',
     'Saved relevance is already classified; preserve job and assessment provenance.'),
    ('PROCESSING_ACTIVE','processing_not_stale','OBSERVE',
     'Wait for worker completion; do not claim an active job again.'),
    ('PENDING','pending_jobs','QUEUE_REVIEW',
     'Inspect claimable work, missing source text, quota and prior assessments.'),
    ('COMPLETED','completed_jobs','COMPLETED_NOT_VERIFIED',
     'Use completion audit to verify evidence and provider lineage before relying on success.'),
)


def assessment_queue_triage(readiness,recovery,superseded):
    """Return a complete, non-overlapping ordinary-job partition.

    Staleness and quarantine are subsets of PROCESSING/FAILED respectively,
    never additional jobs. Pending eligibility subcounts are advisory
    subsets and must not be added to the total.
    """
    counts=recovery
    buckets=[{'code':code,'count':max(0,int(counts.get(key,0))),
              'priority':priority,'next_step':guidance}
             for code,key,priority,guidance in _BUCKETS]
    by={row['code']:row['count'] for row in buckets}
    total=max(0,int(counts.get('total_ordinary_jobs',0)))
    partition_total=sum(by.values())
    ready=readiness.get('queue_counts') or {}
    pending=max(0,int(by['PENDING']))
    claimable=max(0,int(ready.get('claimable_pending_with_text',0)))
    missing=max(0,int(ready.get('pending_missing_source_or_text',0)))
    assessed=max(0,int(readiness.get('pending_already_assessed_excluded_from_ai',0)))
    exhausted=max(0,int(ready.get('pending_attempts_exhausted',0)))
    pending_known=claimable+missing+assessed+exhausted
    # The four groups are disjoint by the existing readiness query. If
    # counts race across independent snapshots, report drift rather than
    # fabricate a residual category or approve provider work.
    consistent=(partition_total==total and pending_known==pending)
    return {
        'scope':'ONE_AUTHORIZED_CAMPAIGN_ORDINARY_JOBS',
        'status':('RECHECK_INDEPENDENT_SNAPSHOTS' if not consistent else
                  'HOLD_FOR_HISTORY_REVIEW' if
                  (by['STALE_PROCESSING'] or by['QUARANTINED_INTERRUPTED'] or
                   by['FAILED_OTHER']) else
                  'QUEUE_RECONCILIATION' if
                  (assessed or missing or exhausted or
                   int(superseded.get('superseded_without_current_classification',0))) else
                  'ACTIVE_PROCESSING' if by['PROCESSING_ACTIVE'] else
                  'PENDING_WORK' if pending else 'NO_ACTIVE_WORK'),
        'buckets':buckets,
        'ordinary_job_total':total,
        'bucket_total':partition_total,
        'buckets_partition_all_jobs':partition_total==total,
        'pending_breakdown':{
            'pending_total':pending,
            'eligible_with_text':claimable,
            'missing_source_or_text':missing,
            'already_assessed':assessed,
            'attempt_limit_exhausted':exhausted,
            'breakdown_total':pending_known,
            'breakdown_reconciled':pending_known==pending},
        'outdated_superseded_classifications':max(0,int(
            superseded.get('superseded_without_current_classification',0))),
        'stale_threshold_minutes':int(counts.get('grace_minutes',10)),
        'historical_provider_usage_not_verified':True,
        'all_snapshots_are_atomic':False,
        'automatically_retried':False,
        'automatic_paid_ai_authorized':False,
        'source_ids_and_provider_errors_exposed':False,
        'additional_database_queries':0,
        'database_writes':0,
        'paid_provider_called':False,
    }
