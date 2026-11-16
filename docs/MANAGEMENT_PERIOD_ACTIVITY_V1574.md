# v157.4 — Cross-period management reporting audit activity

Original case-creation cohort KPIs are retained to avoid silently changing management denominators. A separate, permission-filtered activity cohort groups five recorded audit-action types by case and selected UTC period. This captures reports reviewed or revised in the selected week even when the underlying assignment originated in an earlier period. Displays distinct cases with observed activity, older cases with activity, event counts for submissions, returns, approvals, revisions, source reviews, and approval events on older cases. Events are not unique report counts, legal determinations or lifetime evidence.

New Activity CSV exports the period-audit cohort, including authorized older cases, without changing the original casework CSV. Word, PDF and Excel share the management report template scorecard and period-activity caveat. Geographic authorization enforced by SQL predicates plus defense-in-depth _visible; no raw audit notes or officer identities are exposed.

No schema change, AI calls, Supabase writes, or live officer actions. QA uses isolated SQLite.
