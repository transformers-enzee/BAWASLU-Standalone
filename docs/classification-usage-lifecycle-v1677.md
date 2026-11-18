# v167.7 — Classification usage lifecycle integrity

The read-only assessment-completion audit now independently flags classification usage associated with non-COMPLETED jobs and multiple classification-usage rows attached to the same assessment version. These are evidence of an inconsistent lifecycle or duplicate accounting records, not proof of a second bill or an instruction to reprocess.

The checks are campaign scoped and exclude watchlist-only job links. Sentiment-only usage is excluded from classification-lineage diagnostics. The operational dashboard exposes a combined exception and requires manual provenance review. No states, usage records, budgets, AI calls or source documents are changed.

Live Supabase aggregates checked before release indicated 180 classification usage rows across 180 distinct assessment IDs, all associated with completed jobs. Synthetic tests cover stale PROCESSING, PENDING with saved usage, duplicate usage, sentiment-only usage, and campaign isolation.
