"""Read-only lifecycle parity across independent campaign aggregate snapshots.

Every ordinary job must appear in exactly one terminal or in-flight state.
Interrupted diagnostics partition PROCESSING into stale and not-stale,
and FAILED into quarantined and ordinary failures. All state comparisons are
recomposed before comparison, with no extra database requests.
"""
_STATES=('pending','processing','completed','failed','superseded_assessed')
_AUDIT_KEYS={'pending':'pending_jobs','processing':'processing_jobs',
             'completed':'completed_jobs','failed':'failed_jobs',
             'superseded_assessed':'superseded_assessed_jobs'}

def assessment_snapshot_consistency(readiness,completion,recovery,superseded):
    q=readiness['queue_counts']
    worker={k:int(q[k]) for k in _STATES}
    audit={k:int(completion[_AUDIT_KEYS[k]]) for k in _STATES}
    interrupted={
        'pending':int(recovery['pending_jobs']),
        'processing':int(recovery['processing_not_stale'])+int(recovery['stale_processing_jobs']),
        'completed':int(recovery['completed_jobs']),
        'failed':int(recovery['other_failed_jobs'])+int(recovery['already_quarantined_for_manual_review']),
        'superseded_assessed':int(recovery['superseded_assessed_jobs']),
    }
    worker_total=int(q['ordinary_jobs'])
    completion_total=int(completion['ordinary_jobs'])
    interrupted_total=int(recovery['total_ordinary_jobs'])
    checks={
        'worker_vs_completion_job_total':worker_total==completion_total,
        'worker_vs_interrupted_job_total':worker_total==interrupted_total,
        'worker_internal_state_total':sum(worker.values())==worker_total,
        'completion_internal_counts':bool(completion['counts_reconciled'])
                and sum(audit.values())==completion_total,
        'interrupted_internal_state_total':sum(interrupted.values())==interrupted_total,
        'worker_vs_completion_per_state':worker==audit,
        'worker_vs_interrupted_per_state':worker==interrupted,
        'completion_vs_interrupted_per_state':audit==interrupted,
        'superseded_count_alignment':
            worker['superseded_assessed']==int(superseded['superseded_assessed_jobs']),
    }
    failed=sorted(k for k,ok in checks.items() if not ok)
    return {'checks':checks,'all_consistent':not failed,
        'failed_checks':failed,
        'recheck_required':bool(failed),
        'validated_queue_states':list(_STATES),
        'stale_processing_kept_in_processing_total':True,
        'quarantined_jobs_kept_in_failed_total':True,
        'aggregate_reads_are_not_atomic':True,
        'database_corruption_proven':False,
        'new_database_queries':0,
        'database_writes':0,'paid_provider_called':False}
