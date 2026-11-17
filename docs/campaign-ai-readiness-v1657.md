# v165.7 — Campaign AI readiness / post-processing queue audit

The live campaign-2 Supabase reconciliation (v165.6) left 29 PENDING ordinary KEYWORD jobs with attempts=0 and zero missing job rows. That is a durable queue, not completed AI analysis.

The existing read-only campaignAIWorkerReadiness action is extended to report, within the already-authorized campaign only: PENDING jobs, claimable PENDING jobs with nonblank original source text, queued jobs missing source text, attempt-exhausted PENDING jobs, PROCESSING, COMPLETED, FAILED, daily and lifetime reservations and remaining request counts. Counts include links older than the last 300 sources. Quota aggregation no longer truncates reservation rows to the first 400. Reasons for unavailable automatic screening are explicit and non-sensitive. 'ready_to_process' is false when no claimable jobs remain or quota is exhausted; it is NOT officer authorization to spend. Estimated next-run requests is an upper bound, never a monetary estimate.

The worker now skips missing or blank original source text before claiming or reserving any request, avoiding unnecessary paid calls. Existing atomic claim and budget reservation logic remains untouched, as do watchlist exclusion, officer authorization and the paid execution switch.

No AI or SocialCrawl providers are called by this release; the report is read-only. No new public route, schema migration or automatic expense is enabled.
