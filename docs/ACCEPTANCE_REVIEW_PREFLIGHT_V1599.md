# v159.9 — Fresh-status verification and conflict recovery

Acceptance Review no longer relies only on a possibly stale paginated list before offering an irreversible human decision. The frontend performs a fresh, no-store GET of the specific authorized submission before presenting confirmation. The new read-only GET /api/assistant-evaluation/acceptance-submissions/{evidence_id} retains nationwide active National Administrator authorization, avoids bulk history reads and cannot mark legal or client acceptance.

A conflict or existing review closes confirmation and refreshes the current page. If POST succeeds but the subsequent list reload fails, the UI explicitly says that the review was recorded and does not invite a duplicate action. POST remains protected by PostgreSQL row locking from v159.5. Automated tests verify authorized detail behavior in isolated SQLite and UI source contracts. Human UAT and real concurrent PostgreSQL race verification are still pending.
