# v157.7 — Cross-period approval reconciliation in Activity CSV

v157.6 reconciled audit approval events with the latest saved case report but the Activity CSV lacked those current status results. Reusing the same permission-scoped reconciliation, CSV now shows latest report status at export time for cases that had an approval event and a clear status: STILL_APPROVED, SUPERSEDED_OR_NOT_APPROVED, NO_SAVED_REPORT. Other event-only cases explicitly show NOT_APPLICABLE_NO_APPROVAL_EVENT and NOT_CHECKED_NO_APPROVAL_EVENT, preventing a false implication their report status was checked. A summary invariant confirms the three approval-state categories add up to distinct cases with approval activity. No new queries were added beyond v157.6, and approval event time remains distinct from current saved status.

Five isolated SQLite tests cover latest approved, superseded draft, absent saved report, no approval event and province scope. No officer data changes, migration, crawling or AI credits.
