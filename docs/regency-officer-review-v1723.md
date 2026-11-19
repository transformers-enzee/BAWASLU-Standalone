# v172.3 — Auditable officer Kabupaten/Kota confirmation

- Add explicit, human-only Kabupaten/Kota confirmation and rejection from
  the source-grounded Intelligence Inbox preview.
- Persist the officer decision in the existing append-only AuditEvent table,
  avoiding any staging database schema change. The event references the
  authorized campaign/source pair and stores the selected official regency
  code, original-source fingerprint, assessment version, reviewer, and rationale.
- Reject changed source text, stale review revisions, unsupported and ambiguous
  region candidates, nonrelevant assessments and unauthorized users.
- Invalidate city verification when source content or saved assessment version
  changes. Preserve every previous audit event on revision/rejection.
- Surface saved city decision to modules already using jurisdiction_status,
  without interpreting a verified city as automatic province permission.
- No paid provider calls, AI reclassification, schema migration, worker
  processing, administrative ACL expansion or alteration of existing officer
  classification records.

City verification remains officer-confirmed source jurisdiction, not
independently verified real-world event location or legal determination.
