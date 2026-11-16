# v157.6 — Approval-event to current report-status reconciliation

A case can have an approval audit event during the selected period while its latest report is now RETURNED or DRAFT. The period-activity panel already separated raw event volume and distinct cases (v157.5); this release further distinguishes cases whose current latest saved report remains APPROVED, cases whose latest saved report is now a different status, and approval activity missing a corresponding saved report.

The calculation is performed after the existing permission-scoped audit aggregation. Only distinct authorized cases with approval events are re-read, in batches of 400 IDs, selecting a single latest report per case using SQL ROW_NUMBER over creation timestamp and ID. No historical report contents or reviewer identities are retrieved. A separate as-of-snapshot label avoids misrepresenting the result as the status at the event time. Case-creation-based approval KPIs and other reporting denominators remain unchanged.

Four isolated database regressions cover approved, superseded draft, missing saved report and province boundaries. No live casework writes, schema changes, provider costs, automated approvals or legal conclusions.
