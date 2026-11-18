# v170.1 — durable pending queue aligns with assessment eligibility

The worker's durable pending-job SELECT now ignores campaign/source rows whose latest saved relevance assessment is complete, *before* applying the batch size. This eliminates head-of-line crowding by already-assessed PENDING jobs while preserving original oldest-first ordering, watchlist exclusions, failed/processing/quarantined state protection, and the worker's final atomic claim and paid-call guards.

Adds SQLite regression cases for 4 completed labels ahead of queued unassessed sources, latest-version revisions from assessed to UNASSESSED and back, and no automatic retries or state mutations. The queue test file is explicitly included in the mandatory Render Docker QA gate. No Supabase schema changes or live records are modified.
