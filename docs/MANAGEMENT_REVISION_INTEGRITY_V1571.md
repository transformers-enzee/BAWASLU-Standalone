# v157.1 — Report revision history and current-approval KPI integrity

Management briefing already used the newest report version for approval and submission KPIs. After the Case #2 UAT return/revise/approve path, management still lacked explicit context distinguishing retained returned versions from current approved outcomes.

This release adds report_version_integrity computed entirely from the same permission-filtered authorized case, report, and audit cohort, without new database queries. It shows historical/superseded versions, superseded returned and approved counts, cases with several report versions, latest approved after return, latest draft after return, and latest returned awaiting revision. UI presents these values as non-approval audit history. No old returned/approved versions inflate current approval totals; no legal clearance is implied. Tests cover success, awaiting-revision, reversed statuses, province-scoped cohorts, and cases without reports.

No casework writes, schema migrations, AI inference or crawling. Automated regression and release build required.
