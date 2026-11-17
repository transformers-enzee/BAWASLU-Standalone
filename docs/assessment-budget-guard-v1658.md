# v165.8 — Paid-assessment reservation integrity

Inspection revealed a billing safety bug in the assessment worker: scheduled and targeted requests required quota reservation, but a non-targeted worker invocation with an explicit `requested_limit` skipped reservation entirely. That path could make paid requests despite exhausted daily or lifetime caps.

This release unconditionally requires a successful atomic reservation before any OpenAI request, regardless of whether the work was scheduled, requested as a bounded batch, or targeted to one source. A denied reservation restores the worker's no-cost PROCESSING claim to PENDING, restores its attempt counter, records a non-sensitive reason and stops the batch. Reanalysis restores COMPLETED state. Existing content guards, per-run caps, conflict-safe selection, watchlist exclusion and provider-failure quarantine remain unchanged.

Regression tests cover false reservation on SQLite, pending/reanalysis restoration, invalid release protection and a check that the provider call remains after reservation. No paid AI requests were initiated by this deployment; no queue state or database schema is migrated. The 29 campaign-2 PENDING jobs remain awaiting separately authorized processing.
