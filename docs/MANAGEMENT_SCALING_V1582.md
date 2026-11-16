# v158.2 — Management reporting synthetic scaling and audit-activity projection

The event-window report previously loaded full case assignment rows to produce group-by case/action counts. It now applies an explicit load_only projection for report and permission fields, excluding notes, tag JSON, suggestion JSON and unused update bookkeeping. Case authorization and topic matching retain their required columns.

Automated benchmark tests on synthetic in-memory SQLite build a 423-case creation cohort and a 420-case audit cohort. They record SQL statements, elapsed wall time and serialized response sizes, assert bounded query-count growth for the >400-case case, guard SQL projections against narrative columns, and ensure Activity CSV remains one row per case with no private notes. The benchmark emits reproducible JSON lines when invoked with pytest -s. Do not represent SQLite elapsed time as production Supabase p95 or a validated percentage improvement. Production benchmark still requires representative staging traffic or a safe read-only performance run.

No schema migration, no officer record changes, no AI calls or paid provider credits.
