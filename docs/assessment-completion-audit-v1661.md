# v166.1 — Completion audit for assessment jobs

Live BAWASLU Supabase inspection on 17 November 2026: 190 jobs marked COMPLETED, of which 180 have an assessment with linked AI usage and 10 do not; all ten discrepancies are in campaign 1. These may be historic records not written by the current usage instrumentation. They are **not** automatically assumed to be failed, nor retried.

A new authorized read-only Social Listening action, `campaignAssessmentCompletionAudit`, returns campaign-scoped summary counts for completed jobs with matching assessment + usage lineage, missing assessments, invalid/UNASSESSED relevance, missing linked usage, usage with invalid relevance, attempts=0, and PENDING/PROCESSING/FAILED counts. It checks **any version** with valid relevance + matching AI usage, so a later manual correction does not accidentally erase proof of a previously billed assessment. It returns no source text, result IDs, private tokens or costs; it never sends provider requests or updates jobs. Access uses the existing campaign scope permission gate.

This release does NOT authorize AI spending or make legal conclusions. Review historical discrepancies with source history before any paid reprocessing. Regression QA verifies correct lineage, later versions, missing/incorrect usage, watchlist exclusion, campaign isolation and no side effects.
