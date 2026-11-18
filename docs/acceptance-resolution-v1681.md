# v168.1 — Operational exception resolution criteria

Each active diagnostic in the unified campaign assessment overview now has a stable, non-identifying **resolution checklist** entry: investigation or no-credit next action, evidence required for clearance, priority (historical provenance before queue cleanup), and the name of an existing read-only preview action where supported. The server does not execute preview, reconciliation, quarantine, paid AI, or any database mutation when presenting this list.

History review remains advisory at campaign level, not a global lock of individually eligible unrelated jobs. An unresolved unknown issue is treated conservatively in the resolution checklist rather than silently ignored. Every resolution requires a refreshed audit to verify the exception count changed; a confirmed no-credit queue mutation is not itself proof that unknown provider billing was resolved.

Existing read-only preview actions are campaignAssessmentInterruptedPreview and campaignAssessmentSupersededPreview. All actual writes still require the existing role checks, confirmation, and separate API action. Regression tests cover priority ordering, unknown codes, zero-count exceptions, clearance evidence, scoped authorization, and UI details. No database schema or live records changed.
