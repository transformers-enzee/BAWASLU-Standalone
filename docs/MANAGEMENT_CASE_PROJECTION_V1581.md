# v158.1 — Lean creation-cohort case queries

After v158.0 reduced report-document and audit-event payloads, the creation-cohort case query still fetched entire CaseAssignment ORM entities. Internal notes, tags JSON, suggested provinces and updated_at are not used by management reporting. This release uses SQLAlchemy load_only to omit those fields while retaining every field required for geographic authorization, topic matching, source excerpt and reporting calculations. Case IDs and statuses remain unchanged.

New automated regressions inspect the actual SQL projection, verify all fields subsequently accessed by management do not generate additional lazy reads, verify summary KPIs/topic filters and verify province-scoped access. No migration, manual casework action or AI provider use. This improves query payload shape but is not a measured production latency/egress claim.
