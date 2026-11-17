# v166.4 — Interrupted assessment recovery with no paid replay

The 17 November 2026 live Supabase assessment queue has a campaign-4 PROCESSING job older than the ten-minute recovery threshold. Previously, background quarantine ran only when both automatic AI switches were enabled; the job remained stuck when disabled.

Two existing authenticated Social Listening actions now expose editor-authorized recovery without activating any AI worker. Preview is read-only and returns aggregate eligible count; Quarantine requires confirm_no_retry_quarantine=true and atomically transitions no more than 100 oldest stale ordinary campaign PROCESSING jobs to FAILED with an explicit 'provider call status unknown; manual review required' marker. It preserves attempts, source assessments and provider budget reservations; does not return source IDs or text, and never requeues or contacts providers. WATCHLIST_ACCOUNT and other campaigns cannot be changed.

This is deliberately a quarantine, not a determination that prior calls failed or incurred no charge. Review provider history before any subsequent paid reanalysis. This release does NOT actually invoke the quarantine action against real records; tests use synthetic SQLite jobs. Regression checks cover idempotency, bounded selections, confirmation, campaign isolation and race-safe state predicates.
