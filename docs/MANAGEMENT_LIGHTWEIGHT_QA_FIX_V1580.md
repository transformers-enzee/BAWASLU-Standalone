# v158.0 — Lightweight reporting independent-reviewer metadata fix

The first bulk v157.9 build failed: officer pilot readiness checks access latest_report.reviewed_by and latest_report.created_by to confirm independent approval; the projected report metadata omitted these necessary identifiers. v158.0 includes only those two IDs in the lightweight projection, in addition to report ID, case ID, status and created_at. Large report-body text and evidence snapshots remain excluded. Regression SQL assertions now verify inclusion of independent-reviewer IDs and exclusion of narrative columns. No authorization semantics, report mutations or schema changes.

Release must pass the complete backend and frontend suites before the feature is considered live.
