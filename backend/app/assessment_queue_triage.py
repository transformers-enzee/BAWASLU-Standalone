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


def assessment_queue_triage(readiness,recovery,superseded,completion=None):
    """Return a complete, non-overlapping ordinary-job partition.

    Staleness and quarantine are subsets of PROCESSING/FAILED respectively,
    never additional jobs. Pending eligibility subcounts are advisory
    subsets and must not be added to the total.
    """
    counts=recovery
    audit=completion or {}
    completed=max(0,int(audit.get('completed_jobs',0)))
    verified=max(0,int(audit.get('verified_usage_backed_completed_jobs',0)))
    history_gaps=max(0,int(audit.get('completed_requiring_manual_history_review',0)))
    latest=audit.get('latest_completion_classification_review') or {}
    latest_issues=sum(max(0,int(latest.get(k,0))) for k in
        ('completed_missing_latest_assessment','completed_latest_unclassified_or_invalid'))
    usage_quality=audit.get('usage_lineage_quality') or {}
    lifecycle_quality=audit.get('classification_usage_lifecycle_quality') or {}
    usage_flags={k:max(0,int(usage_quality.get(k,0))) for k in (
        'campaign_id_mismatch','provider_usage_not_reported',
        'negative_token_counts','provider_model_missing')}
    lifecycle_flags={k:max(0,int(lifecycle_quality.get(k,0))) for k in (
        'noncompleted_jobs_with_classification_usage',
        'assessments_with_duplicate_classification_usage')}
    quality_available=(completion is not None and
        'usage_lineage_quality' in audit and
        'classification_usage_lifecycle_quality' in audit)
    flagged=any(usage_flags.values()) or any(lifecycle_flags.values())
    integrity={
        'status':('AUDIT_UNAVAILABLE' if not quality_available else
                  'REVIEW_REQUIRED' if flagged else 'NO_RECORDED_ISSUES'),
        'usage_rows':max(0,int(usage_quality.get('assessment_linked_usage_rows',0))),
        'usage_flags':usage_flags,
        'lifecycle_flags':lifecycle_flags,
        'flag_counts_may_overlap':True,
        'not_evidence_of_provider_charges':True,
        'read_only':True,
        'automatic_retry_permitted':False,
    }
    completion_provenance={
        'completed_jobs':completed,
        'usage_backed_completed':verified,
        'requires_historical_usage_review':history_gaps,
        'latest_classification_review':latest_issues,
        'completed_partition_reconciled':completed==verified+history_gaps,
        'historical_usage_is_not_latest_classification_proof':True,
        'automatic_reassessment_permitted':False,
    }
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
    completion_snapshot_reconciled=(completion is None or
        (completed==by['COMPLETED'] and completion_provenance['completed_partition_reconciled']))
    consistent=(partition_total==total and pending_known==pending and completion_snapshot_reconciled)
    return {
        'scope':'ONE_AUTHORIZED_CAMPAIGN_ORDINARY_JOBS',
        'status':('RECHECK_INDEPENDENT_SNAPSHOTS' if not consistent else
                  'HOLD_FOR_HISTORY_REVIEW' if
                  (by['STALE_PROCESSING'] or by['QUARANTINED_INTERRUPTED'] or
                   by['FAILED_OTHER'] or history_gaps or latest_issues or flagged) else
                  'QUEUE_RECONCILIATION' if
                  (assessed or missing or exhausted or
                   int(superseded.get('superseded_without_current_classification',0))) else
                  'ACTIVE_PROCESSING' if by['PROCESSING_ACTIVE'] else
                  'PENDING_WORK' if pending else 'NO_ACTIVE_WORK'),
        'buckets':buckets,
        'completion_provenance':completion_provenance,
        'provider_usage_integrity':integrity,
        'completion_snapshot_reconciled':completion_snapshot_reconciled,
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
