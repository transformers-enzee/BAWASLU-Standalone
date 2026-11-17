# v165.0 — Bulk job reconciliation reliability

The preceding read-only Supabase audit found 29 ordinary KEYWORD campaign links (all in campaign 2) whose latest saved relevance assessments are UNASSESSED with no AI assessment job, while 37 WATCHLIST_ACCOUNT links have no assessments by design. These two populations must not be conflated. No historical assessment or saved officer sentiment is overwritten in this release.

The existing explicit campaignAssessmentJobReconcile action now selects up to 200 eligible original source IDs per invocation, oldest first, through one bounded query. It checks the latest saved assessment version, excludes every WATCHLIST_ACCOUNT link, and excludes any campaign-result pair that already has an assessment job. PostgreSQL and SQLite unique-key conflict-safe insert ensures overlapping reconciliation requests do not create duplicate jobs. Existing worker callers reuse the same enqueue helper. Failed, completed and processing jobs are never reset or retried by reconciliation. The permission check remains in the campaign route; the helper is not a public endpoint.

Reconciliation only creates PENDING job metadata for later separately authorized/budgeted processing. There are no paid OpenAI calls, SocialCrawl credits, new public screens, assessment writes or schema migrations. The existing dry_run preview and worker readiness endpoint remain available; the explicit reconcile response includes updated per-campaign link coverage.

The historical worker's 300-source processing window and real Render-to-Supabase performance remain separate future verification concerns. Actual staging AI screening is NOT automatically enabled by this release.
