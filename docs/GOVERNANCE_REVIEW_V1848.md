# BAWASLU v184.8 — independent approval and officer QA readiness

## What is implemented
- Gate 2 approval is now **independent for every insight**, not only high-impact findings.
- Approval source snapshot incorporates the latest legacy officer sentiment correction and the latest evidence review associated with the current AI assessment, in addition to original source, assessment and the new correction ledger. A later officer action makes an approved insight stale.
- The opt-in Inbox governance overlay now shows the real saved AI sentiment alongside proposed governance corrections. It **flags disagreements** with the existing officer sentiment ledger; it does not overwrite the legacy effective sentiment.
- Added bounded, permission-scoped `GET /api/governance/review-queue` to show review, reassessment and approval eligibility for officers.
- Added administrator-only `GET /api/governance/readiness` reporting governance table/RLS prerequisites and feature-flag states. Read-only and no AI/provider charges.
- Offline tests cover snapshot invalidation, conflict reporting, independent approval and readiness/queue opt-in.

## Current safety state
- New governance tables already exist in the shared Supabase project, with RLS and direct anon/authenticated reads disabled.
- `BAWASLU_GOVERNANCE_WRITES_ENABLED` and `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED` remain **off by default**.
- Existing Inbox, Command Centre, officer sentiment corrections, and all source records are unchanged by default.
- This is not production enforcement of official publication: the approved-only governance projection remains separate from legacy preliminary dashboard signals.

## Acceptance criteria before asking an officer to perform manual QA
1. Activate the read-only flag on staging only; check administrator readiness and two officer roles with correct campaign/jurisdiction scopes.
2. Verify legacy correction conflicts and independent reviewer eligibility in representative source/insight cases.
3. Only after controlled backup and approvals, activate governance writes for an isolated pilot, then manually test one correction, one pending insight, one independent approval and a subsequent invalidation.
4. Confirm all activity is audit-visible and no paid AI requests are made during QA.
