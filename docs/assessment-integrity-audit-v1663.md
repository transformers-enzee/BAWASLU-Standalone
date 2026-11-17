# v166.3 — Read-only provider usage and interrupted-worker integrity audit

Live 17-Nov-2026 Supabase investigation identified 290 usage records: no cross-campaign mismatches, negative token counts, missing provider model names or usage_reported=False. However 10 historical campaign-1 completed jobs have no linked AI usage and one campaign-4 job remains PROCESSING after the 10-minute interrupted-worker threshold.

The authorized campaignAssessmentCompletionAudit action now adds campaign-scoped aggregates for usage row quality and stale PROCESSING jobs. Missing usage history and stale provider work are **review states**, never automatic retry instructions. The code never edits source records, assessment jobs, officer casework or usage. It returns no source text or identifiers and never calls an external provider.

Historical completion checks remain separated from provenance checks: the ten legacy missing-usage jobs are not replaced with invented usage data. This batch adds three focused automated tests for campaign isolation, malformed usage, historical state preservation and the no-error empty case. Actual successful processing remains a separately authorized and budgeted activity.
