# v172.9 — Review any authorized campaign evidence without page-window dead ends

## Functional improvements
1. Use descending campaign-evidence ID keyset navigation through bounded
   30-link batches of jurisdiction readiness. Each view clearly identifies
   its page cursor and whether more source links exist; no results are
   extrapolated into a whole-campaign completion percentage.
2. Remove the "visible Inbox page only" restriction on jurisdiction review
   leads. The officer can request the exact authorized saved source from
   the existing Intelligence Inbox action, which already supports
   campaign-scoped deep-link lookup outside the normal page window.
3. Exclude watchlist-account-only evidence from the jurisdiction review
   queue, aligning the queue to the Intelligence Inbox evidence population.
4. Add isolated regression tests for keyset integrity, cursor rejection,
   cross-campaign access, and exact older-source lookup. Include frontend
   contract checks in the existing CI acceptance suite.

## Safety and limits
Actions require the same authenticated campaign and source permissions;
no new paid AI/provider calls, migrations, officer corrections or implicit
jurisdiction confirmations. Existing historical review decisions are preserved.
Sample counts are per 30-link window, not full-corpus accuracy or acceptance.
