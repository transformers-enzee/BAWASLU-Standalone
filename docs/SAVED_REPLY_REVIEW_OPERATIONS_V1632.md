# v163.2 - Owner review operational readiness

Owner-scoped persisted review summaries expose bounded next-action counts, current completion and stale recheck counts; no evidence content or cross-user activity is included. The reviewer can refresh status without writing records. Each saved review supplies a deterministic next-action label, not an accuracy or legal verdict.

Audit-history retrieval remains authorized to the record owner, even when the original saved answer has changed or become ineligible. The endpoint returns the latest 50 events in chronological order with an explicit history-truncated flag and total recorded version count, avoiding the misleading oldest-100 limit. Historical event rows are not deleted. No model calls, database migration or external signoff.

Automated tests cover owner isolation, stale-history accessibility, attention counts and a 56-version event trail.
