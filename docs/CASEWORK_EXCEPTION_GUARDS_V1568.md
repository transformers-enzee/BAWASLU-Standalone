# v156.8 — Officer casework negative-path QA and original source guard

After two staging UAT cases passed core assignment, return, revision and independent approval, the next automated exception batch focuses on three trust boundaries:

1. Original source access: only a syntactically valid HTTP(S) link with a hostname and no embedded credentials can support SOURCE_CHECKED. A ticked confirmation without an eligible link is rejected, while officers may record SOURCE_UNAVAILABLE without claiming to have opened the source. This reuses the pilot intake URL validity predicate for consistent source handling.
2. Independent approvals: author cannot approve own submission; nonauthorized reviewers cannot approve. These guards already existed, and dedicated negative regression coverage verifies they remain intact.
3. Jurisdiction: an unverified province mention cannot authorize provincial assignment; confirmed province Riau cannot be rerouted as Bali. Existing routing safeguards are covered with isolated negative tests.

No live cases or report approvals, permission changes, Supabase schema migration, crawling credits or model inference. Manual QA required only if automated tests or deployment expose a behavior gap.
