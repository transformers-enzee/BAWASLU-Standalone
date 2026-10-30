# BAWASLU end-to-end rehearsal — actual evidence (staging)

## Scope and measured baseline
- Supabase currently stores 463 captured Social Listening sources; campaign 1 links 298 distinct sources.
- These are database counts, **not** evidence that every source is current, relevant, or approved.
- Existing caches: Inbox scope-keyed RAM TTL 45s (raised to 90s in v112.2); Social Listening dashboard RAM TTL 600s (reduced to 180s for freshness); Command Centre pilot source/topic caches are already present.
- Cache is per application process. It does not eliminate high SQL query counts on cold load.

## Walkthrough and checkpoints
1. **Discover and track:** open BAWASLU campaign Social Listening. Verify saved captured posts display source URL, platform, capture provenance and date. Demonstrate saved searches/discovery separately from captured records; do not claim a live crawl happened unless provider-run logs prove it. Compare watchlist candidate profiles with their *separate* account-scoped feed. Watchlist ingestion is opt-in, with credit budget and first-page limits; never confuse account mentions with verified candidate statements.
2. **From evidence to assessment:** choose a saved BAWASLU post referencing an election complaint (for example source 225). Verify original text, source link, campaign assignment, latest assessment version, sentiment and any explicit allegation/concern signals. Status must remain unverified until an officer verifies it. Record ID, not just an AI description, must travel to downstream screens.
3. **Intelligence Inbox:** confirm the same source ID is visible to the authorized officer with review state and source-linked evidence; inspect public-concern/violation signals and correct stale labels without deleting prior assessment versions. No matching source must be silently promoted to a verified case.
4. **Command Centre:** verify Level 1 player counts use the same authorized evidence and the distinction between allegation, public concern and recurring narrative. Drill from the summary to source 225. For a procedural concern use post 184 as a separate test case (reported limits on Bawaslu candidate-document access). Verify the geographic view does not turn post geotags into confirmed incident locations.
5. **AI Assistant:** ask “What evidence is there about public concerns over Bawaslu oversight, and what remains unverified?” and “Which saved posts report potential electoral violations and what should officers verify next?” Check that answers cite available intelligence IDs and explicitly acknowledge missing verification. The Assistant is limited to authorized records, is read-only, and does not have permission to invent facts or validate incidents.
6. **Negative tests:** ask for evidence beyond the user's jurisdiction and for an unsupported allegation. Ensure no cross-scope evidence leak, no hallucinated legal verdict, and no made-up citations.

## Acceptance criteria
- Warm navigation is faster than cold navigation when identical scope and data are unchanged; record browser timings and Render request latency for each of four screens.
- Cache invalidation after officer corrections; cross-user and cross-jurisdiction isolation; no stale positive verdict after flag dismissal.
- Main feed/watchlist and source-detail navigation works; captured source identifiers survive all hops; labels and dates remain consistent.
- The paid AI answer path is tested with a known permitted question and explicitly verified response provenance.

## QA status
This file is a reproducible test plan and database-supported sample selection, not a report of completed browser E2E tests. No live provider credits or OpenAI call were executed by authoring it. Render latency, actual watchlist external retrieval and signed-in UI navigation still require execution.
