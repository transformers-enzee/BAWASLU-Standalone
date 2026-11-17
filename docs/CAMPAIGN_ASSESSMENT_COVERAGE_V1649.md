# BAWASLU v164.9 — Separate excluded watchlist links from AI assessment backlog

A read-only 17 November 2026 Supabase audit found 636 campaign-evidence links. The 37 links without any assessment were all `WATCHLIST_ACCOUNT` associations intentionally excluded by ordinary campaign assessment and job-enqueue logic. The separate actionable gap was 29 `KEYWORD` campaign links whose latest saved assessment row had relevance label `UNASSESSED` and no saved job; the assessment row's existence alone was not proof of completed screening.

The existing authorized `campaignAIWorkerReadiness` response now supplies an aggregated assessment-link inventory for the selected permitted campaign, explicitly separating excluded watchlist associations, normal monitoring links, assessed links, links still pending relevance, those without a job, and those with a recorded job (including FAILED). The query runs only when this existing readiness action is called; it does not add egress to routine Radar or Inbox loads. No source text, identifiers or officer information are returned.

The existing editor-only `campaignAssessmentJobReconcile` action now accepts `dry_run=true` to return the same no-cost readiness inventory without creating jobs. Its existing explicit, authorized non-preview behavior still enqueues unassessed monitoring jobs, excluding watchlist associations, and does not call a paid provider. No automatic paid requests, schema changes, officer record edits or new development-only UI were introduced.

The aggregate is per authorized campaign and does not imply whole-database completion; an `UNASSESSED` latest label is still pending even if the source has saved historical assessment rows.
