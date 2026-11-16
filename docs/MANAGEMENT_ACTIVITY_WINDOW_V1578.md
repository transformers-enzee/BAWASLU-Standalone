# v157.8 — Efficient Activity CSV with explicit UTC provenance

The v157.7 Activity CSV previously called scoped_cases() only to obtain validated period bounds, unintentionally fetching the full creation-period assignment cohort before its separate permission-scoped audit event query. This was redundant in a potentially high-traffic management export. The common period validator now returns UTC bounds and normalized topic without reading case rows. Both original scoped_cases and Activity CSV reuse the validator, preserving permissions, topic length and allowed-period checks while eliminating the CSV-only extra assignment retrieval.

The CSV carries explicit selected UTC start/end and the timestamp used for the latest-report status snapshot. Matching non-sensitive response headers expose the window for an empty CSV as well. Approval event dates and status-observation time remain conceptually separate. Tests verify equivalent period validation, no creation-cohort read, exact window headers and columns, rejection of bad filters, and geographic access boundaries.

No schema changes, no writes to Supabase, no casework approvals or AI/provider cost.
