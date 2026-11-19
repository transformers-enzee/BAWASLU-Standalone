# v172.7 — Multi-track jurisdiction delivery and measurable readiness

## Track A — Read-only campaign jurisdiction readiness
A new on-demand campaign snapshot reports actual authorized sampled posts,
saved relevance, unverified location cues, ambiguity, officer confirmations,
rejections and stale/conflicted decisions. Scan size is capped at 30 recent
campaign evidence links to bound cost. The API explicitly reports truncation
and never extrapolates full-corpus coverage or equates decision coverage with
geographic accuracy, product completion or client signoff.

## Track B — Location recognition correctness
The incident-locality detector can now follow up to eight contiguous,
explicitly connected region mentions rather than dropping the third and
later city. All names must resolve to the official region registry and no
automatic location confirmation is issued.

## Track C — Cross-module acceptance
Tests verify officer-confirmed or rejected city decisions are consistently
visible in authorized Intelligence Inbox and Watchlist saved classifications,
without changing province-level access. Negative, unauthorized, ambiguous,
and truncated results have focused coverage.

Only read-only campaign status queries and local test fixtures are added;
no paid AI/provider calls, officer-record modifications, migrations, or
new background polling are triggered by the build.
