# v100.4: canonical source reuse (engineering scope)

The role-scoped GET /api/source-lineage/saved-assessments/social:<id> returns latest relevant saved campaign assessments, with immutable version information and human concern provenance. This same contract is reusable by Inbox, Watchlist, and any Smart Radar view that **explicitly owns a verified social source ID**.

No automatic mapping from separate radar pilot IDs is allowed. The endpoint returns HTTP 409 for radar:* without a verified crosswalk. This limitation means Thursday item #13 remains IN PROGRESS for unrestricted pilot-to-social mapping, notwithstanding verification of the common social source contract.

Workflow QA includes a mocked versioned officer correction, shared saved assessment read, authorization denial, and radar namespace refusal. No credit spending, reclassification, or production records changed. Prior workflow tally remains 8/15.
