# v157.5 Distinct case activity versus audit-event counts

The existing period-activity panel represented recorded event totals, not necessarily different cases. Multiple report submissions, returns or approvals on one case can inflate perceived workload. This release adds distinct affected-case counts for submissions, returns, approvals, revisions and source reviews, plus separate distinct older cases with approval events. Values reuse the permission-filtered SQL grouping from v157.4, without additional DB queries. The Activity CSV now includes one row per case with explicit activity indicator columns.

No alteration of creation-period KPIs or latest approved-report counts; observing an approval event is not proof the latest report is currently approved, nor legal or client acceptance. No live case writes or database migration. Four SQLite regression tests cover repeated events, old cases, CSV and geographic boundaries.
