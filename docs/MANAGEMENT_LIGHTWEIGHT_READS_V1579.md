# v157.9 — Low-egress management casework projections and large-cohort batching

Reports & Briefings previously loaded complete CaseReport and CaseTransition ORM objects for every case created in the selected reporting period. Report bodies (findings, narratives, evidence snapshots, reviewer comments) were fetched although management metrics only need report ID, case ID, status and creation time. The audited source-review checks require event ID, case ID, action, details_json and event timestamp, but not actor identity or unrelated columns.

This release projects only those required fields, preserving latest-report selection, historical revision metrics, reviewer workflow counters, CSV status, and evidence-progress calculations without fetching large report text blobs. The case-ID list is processed in 400-ID batches to keep SQL bound lists moderate for large cohorts. No changes to the audit-event-date cohort and no Supabase schema migration. Full automated regressions verify UAT version integrity, SQL selection, source-review details, >400-case batching, and geographic permissions.

This is a structural reduction of transmitted columns, not a measured end-to-end latency claim. Benchmark representative large staging datasets before asserting a specific speed or egress improvement.
