# v172.4 — Bulk officer jurisdiction review consistency and traceable acceptance

- Keep an immutable bounded officer decision history accessible from the authorized Inbox.
- Add an assessment-version precondition to avoid confirming a location against an outdated relevance assessment.
- Serialize campaign review writes with PostgreSQL FOR UPDATE and check the latest audit revision after lock acquisition; SQLite sequential compare-and-swap remains covered in tests.
- Block attempts to change the province in a way that contradicts an existing verified city.
- If historical conflicting province and city confirmations are found, fail closed on city verification rather than silently presenting both as true.
- Preserve source-text fingerprint checks, campaign access, human-validation permission, and append-only decisions.
- Add five isolated backend cases and CI contract coverage; keep older review regression scenarios intact.
- No paid AI calls, database migrations or permission expansion.

Boundary: the officer-reviewed jurisdiction is evidence-supported and audit-traceable,
not independently verified real-world incident location or a legal determination.
