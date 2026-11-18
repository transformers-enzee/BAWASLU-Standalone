# BAWASLU v171.5 — Administrator review safeguards

This release extends the v171.4 read-only exception triage and does **not** alter
officer assessments, job status, Supabase rows, provider calls, or quota reservations.

## Interpretation rules

1. Campaign aggregate consistency must agree with queue-level reconciliation before
   the screen presents the snapshot as reconciled.
2. Missing provider-usage integrity or completion-provenance audits are **unknown**
   rather than clean. The next step is to restore the read-only audit.
3. Unknown exception categories stay within history review and cannot silently pass.
4. Repeated exception codes are grouped into one category, but flag counts may overlap
   across codes and must never be summed as unique jobs.
5. Even with a clear queue, no exception categories, and both audits present,
   independent provider billing/usage verification is **not** asserted.

## Automated QA

- Backend: `backend/tests/test_assessment_exception_review_v1715.py`.
- Frontend contract: `node frontend/scripts/test-assessment-exception-review-v1715.mjs`.
- Full CI: backend pytest, frontend production build, Playwright, security,
  visual parity, and officer UI acceptance workflows.
