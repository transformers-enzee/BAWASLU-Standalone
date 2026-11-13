# BAWASLU v154.7: Pilot active-case coverage and safe ID validation

### Root cause
v154.4 introduced a read-only officer pilot shortlist, but its matching active-case query fetched the latest 250 authorized cases for the selected source IDs and then filtered locally. A large cluster of repeated casework for source A could use up the 250-row result budget and hide an active case for source B. The shortlist might then show a new-assignment action for B despite an existing visible active case. The separate POST assignment endpoint had already been made idempotent, so this did not allow duplication by a single authorized officer, but the discovery UI could still mislead.

### Implementation
- Added `_pilot_visible_active_cases` in the existing casework backend. It filters by the authorized SQL scope, the exact 12 source ID / campaign ID pairs from the shortlist and non-CLOSED status, then uses SQL `row_number()` partitioned by (source_id,campaign_id) to fetch the **latest active visible assignment for each exact pair**. No 250-row arbitrary global cap, no case IDs from unauthorized jurisdictions and no per-case query loop.
- Preserved the subsequent `_visible` jurisdiction check as defense in depth. Existing case reuse remains a navigation hint; the POST casework endpoint always rechecks saved source and permissions independently.
- Added explicit lookup metadata to distinguish per-pair latest-active coverage from the 12-row shortlist preview.
- Hardened the shortlist source/campaign ID parser to reject booleans, oversized numeric strings, values outside signed 64-bit range, non-ASCII digits, forged query separators and negative IDs before SQL or URLs. This also prevents Python's integer-string conversion limit from causing an unhandled exception when an inbound source ID is thousands of digits.
- Added regression tests for 260+ existing case records where one source previously obscured another, exact campaign partitioning, closed-case exclusion, province separation, 12-pair cap, valid/invalid IDs and a read-only on-demand pilot call.

### Constraints
Single bulk sequential staging push, automated QA mandatory, Supabase main database, no migrations, no new provider/AI spend, no live officer casework writes and no automatic approvals. Formal human officer acceptance remains separate.
