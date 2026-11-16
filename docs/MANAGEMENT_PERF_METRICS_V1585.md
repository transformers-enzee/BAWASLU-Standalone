# v158.5 — bounded aggregate reporting diagnostic improvements

The opt-in, National Administrator-only read-only performance sample now separates **management report-building time** from **JSON serialization time** and records aggregate max/average successful SQL-statement driver times. It also returns an overall instrumented time inclusive of serialization. SQL text, query parameters, identities, cases, report content and source URLs remain excluded.

Measurements are **not** HTTP latency, full Render-to-Supabase network breakdown, server response transmission, load testing or p95. Profile authorization remains outside instrumentation. The maximum query duration is a database-driver statement timing, not query plan evidence. The existing diagnostic remains disabled unless `BAWASLU_REPORT_PERF_ENABLED=1` is explicitly set; disable after authorized measurements. This release does not change officer casework, database records, approvals or regular report outputs.

Interpretation: if DB-driver time dominates report generation, investigate scoped reads, indexes and query plans; if non-driver time dominates, inspect Python report assembly; if serialization dominates, inspect response size and serialization. Actual staging results are required before claiming a bottleneck or improvement.
