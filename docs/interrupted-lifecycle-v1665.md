# v166.5 — Interrupted worker lifecycle reconciliation

The read-only campaignAssessmentInterruptedPreview now reports stale and fresh processing jobs, previously quarantined unknown-provider-call jobs, other failed jobs, pending, completed and aggregate total ordinary jobs. This separates historical failed states and does not reveal evidence IDs, source text or provider details.

The explicitly confirmed quarantine action now reports how many old jobs remain beyond the recovery cutoff after processing a bounded batch. Its conditional SQL UPDATE revalidates not only the original state, campaign and updated_at, but also the existence of an ordinary non-watchlist campaign-evidence link. This closes a race where the evidence link might change after the preview/ID scan. Quarantine still never returns any job to PENDING; attempts and provider reservations are preserved.

The existing campaign-4 stale job is not mutated by this deployment. Separate editor confirmation and a manual history review remain necessary for changing its state. The v166.5 synthetic regression tests verify repeat execution, watchlist/campaign isolation, correct post-operation totals and SQL preconditions. No paid providers are called.
