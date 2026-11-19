# v171.9 — Cross-diagnostic consistency safeguards

- Detect contradictions between provider-usage diagnostic flags and the top-level exception inventory.
- Detect historical completion provenance gaps not represented in exception issues.
- Detect unreconciled completed partitions, queue-level snapshot retry states, and self-contradictory snapshot reports.
- Hold advisory manual capacity at zero and request a refreshed read-only snapshot when such conditions occur.
- Show an administrator-facing diagnostic inconsistency warning, without exposing raw provider errors or identifiers.
- Wire the v171.9 static contract test into the existing CI workflow; add six pure backend tests and one isolated browser scenario.

This release adds no database reads/writes, migrations, officer-record mutations, quota reservations or paid AI calls.
