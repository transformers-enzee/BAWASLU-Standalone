# v166.2 — Read-only historical AI usage provenance triage

Supabase investigation, 17 November 2026: of 190 completed assessment jobs, 10 campaign-1 jobs lack any linked usage row. The ten were created on 28 October 2026, have one recorded job attempt each, and have 3–8 saved assessment versions. Their latest model label is PRISM_OPENAI_TOPIC_CLASSIFIER, which describes only the **latest** assessment, not necessarily the model that originally processed the job. This evidence does **not** establish whether the earlier AI provider billed the job or why an AI usage row is missing.

The authorized `campaignAssessmentCompletionAudit` action now returns a historical triage summary for completed jobs with valid saved relevance but no linked AI usage: total, attempts>0, multi-version counts, earliest and latest job-created dates, and at most ten latest-model count buckets. No source text, post IDs, provider credentials or individual record details are exposed. The cause is explicitly UNDETERMINED, historical records stay untouched, and automatic reprocessing remains forbidden.

Automated QA covers mixed historical attempts, successive assessment versions, usage-backed completion, cross-campaign and watchlist exclusions, no-gap responses and no database mutation. The work does not spend AI or social crawling credits.
