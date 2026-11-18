"""No-extra-query parity check across independently read campaign aggregates.

The component metrics may be read at different instants. Differences are
reported as snapshot inconsistencies, not asserted as corrupted database rows.
"""
_STATES=('pending','processing','completed','failed','superseded_assessed')
def assessment_snapshot_consistency(readiness,completion,recovery,superseded):
    q=readiness['queue_counts']
    checks={
        'worker_vs_completion_job_total':int(q['ordinary_jobs'])==int(completion['ordinary_jobs']),
        'worker_vs_interrupted_job_total':int(q['ordinary_jobs'])==int(recovery['total_ordinary_jobs']),
        'completion_internal_counts':bool(completion['counts_reconciled']),
        'worker_vs_completion_per_state':all(
            int(q[k])==int(completion[{
                'pending':'pending_jobs','processing':'processing_jobs',
                'completed':'completed_jobs','failed':'failed_jobs',
                'superseded_assessed':'superseded_assessed_jobs'}[k]])
            for k in _STATES),
        'worker_vs_interrupted_per_state':all(
            int(q[k])==int(recovery[{
                'pending':'pending_jobs','processing':'processing_not_stale',
                'completed':'completed_jobs','failed':'other_failed_jobs',
                'superseded_assessed':'superseded_assessed_jobs'}[k]])
            for k in ('pending','completed','superseded_assessed')),
        'superseded_count_alignment':int(q['superseded_assessed'])==int(superseded['superseded_assessed_jobs']),
    }
    failed=sorted(k for k,ok in checks.items() if not ok)
    return {'checks':checks,'all_consistent':not failed,
        'failed_checks':failed,
        'recheck_required':bool(failed),
        'aggregate_reads_are_not_atomic':True,
        'database_corruption_proven':False,
        'new_database_queries':0,'database_writes':0,'paid_provider_called':False}
