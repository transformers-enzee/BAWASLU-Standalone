# v170.3 queue diagnostic partition

The campaign-scoped, administrator-readable assessment operations overview now provides queue_triage, derived solely from existing read-only aggregates without new queries. It partitions ordinary jobs into stale processing, active processing, quarantined interruptions, other failures, superseded assessments, pending and completed. Pending jobs are further broken into claimable, missing source text, already assessed and exhausted attempts; partitions are checked for consistency and non-atomic-snapshot drift is explicitly flagged.

It does not include post IDs, source text, provider errors, authorization to perform AI work, job-state mutations or automatic retry. Synthetic regression tests cover cross-campaign and watchlist exclusions, full state partitions, stale cutoff, count drift and historical usage uncertainty.
