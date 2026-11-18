# BAWASLU v167.3 — Atomic AI claim guard for already-classified evidence

The worker previously allowed an ordinary PENDING queue job to enter AI processing when its relevance label was already assessed but auxiliary enrichment remained incomplete (`needs_full_assessment`). This conflicted with the manual batch-preview's criteria and could cause unnecessary paid provider requests. The worker now distinguishes normal pending processing from explicitly authorized reanalysis: any existing latest RELEVANT/IRRELEVANT/UNCERTAIN classification prevents an ordinary pending call, irrespective of enrichment state.

An SQL-level correlated latest-version guard is also added to the atomic PENDING→PROCESSING UPDATE. This closes the interval where another assessment could be saved after the worker read the previous version but before the job claim. The conditional update must affect one row before any budget reservation or provider request.

All existing budget safeguards remain in effect. Synthetic SQLite tests verify race-time assessment changes, latest-version precedence, terminal SUPERSEDED_ASSESSED blocking, and claim-before-budget ordering. No live queue rows or provider usage records were changed by this release.
