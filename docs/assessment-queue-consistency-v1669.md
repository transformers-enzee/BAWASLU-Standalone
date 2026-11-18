# v166.9 — Queue eligibility reconciliation

The worker-readiness summary previously counted any PENDING job with original post text as claimable, even when the post already had a valid, latest relevance classification. The separately authorized manual assessment preview correctly excluded those posts. As a result, the unified panel could overstate work eligible for paid processing.

This release aligns the worker-readiness calculation to the **latest** assessment-version label, distinguishing empty/UNASSESSED from RELEVANT/IRRELEVANT/UNCERTAIN. It separately exposes aggregate `pending_already_assessed_excluded_from_ai` and flags a PENDING_ALREADY_ASSESSED review item. The system does not automatically mark the job complete or replay an already-assessed post. This is a read-only reconciliation and cannot incur provider charges.

Synthetic tests verify changed human assessment versions, campaign isolation, watchlist exclusion, source-text guard, preview-versus-readiness parity and zero provider calls. No database schema changes or officer records are modified.
