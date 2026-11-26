# BAWASLU SmartRadar v184.6 - Governance projection and stale-evidence safety

This is a staging-only additive code batch, with no automatic migration or paid provider calls.

## Data and schema verification
- Read-only Supabase metadata check on 26 Nov 2026: existing source/assessment/campaign tables present.
- The two v184.5 governance tables **are absent** from the shared BAWASLU Supabase schema.
- Do not enable `BAWASLU_GOVERNANCE_WRITES_ENABLED` on staging yet. It remains OFF.
- Do not execute Alembic migrations automatically on Render. Existing production-aligned data and UI remain unchanged.

## v184.6 changes
1. Effective-value read projection for the supported, directly mapped fields `sentiment` and `relevance`, respecting latest approved officer correction per field. Unmapped correction fields are disclosed, never silently applied.
2. Record-level human-verified status remains false for a single field override. Do not conflate classification review with source verification.
3. Complete content/assessment/correction digest binds approval to its source revisions, not just a single correction ID.
4. Approved-only read API `GET /api/governance/command-centre/approved?campaign_id=...` dynamically re-evaluates evidence freshness and publication conditions; no legacy Command Centre writes.
5. Client-provided evidence verification flags are rejected for new proposals. Verified claims cannot be self-certified; high-impact approval requires an independent officer, with server-derived high-impact review.
6. Added regression cases for changing source text, AI assessment, correction history, stale approved insights, scope and opt-in defaults.

## Remaining before activation / production use
- Apply additive migrations only after formal authorization and isolated staging schema test; verify RLS and backend credentials.
- Integrate corrected values into actual Intelligence Inbox queries, aggregation and downstream synthesis with a single audited precedence contract.
- Implement review queue, official insight publish operation and UI with RBAC at every write boundary.
- Implement Gate 3 approved learning dataset and model deployment approvals.
- Test concurrent review/approval on Postgres and actual deployment smoke tests, then manual officer acceptance QA.

Neither the existing Command Centre dashboards nor pre-existing social listening records are modified by this release.
