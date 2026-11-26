# BAWASLU v184.5 - governance persistence bulk integration

**Staging branch only.** This batch supplies additive SQLAlchemy models, an additive Alembic migration, an opt-in API for field-level human corrections, evidence-scoped insight proposal, and Gate 2 approval checks. Current Command Centre data is NOT rewritten or published from this new workflow.

## Deployment controls
- `BAWASLU_GOVERNANCE_WRITES_ENABLED` is OFF by default (HTTP 503 for new routes).
- No schema upgrade is run automatically by Render startup (`BAWASLU_STARTUP_READ_ONLY=1`).
- After explicit staging schema review, additive migration `20261126_01` must be applied and validated before enabling the new API. Shared Supabase is not modified by this commit.
- New tables have RLS enabled, and public/anon/authenticated table and sequence privileges revoked. Only the existing authenticated application backend's privileged database role can access them.
- Existing Inbox and Command Centre calculations remain unchanged; these new APIs are a review ledger, not a replacement for legacy read paths.

## Gate coverage
- Gate 1: officer-authorized, jurisdiction-scoped, append-only correction history with optimistic revision guards.
- Gate 2: proposal and explicit authorized decision; source membership and hash snapshot rechecked before approval. High-impact insight cannot be approved by its own proposer.
- Gate 3: remains a pure fail-closed evaluation contract (v184.3); persistent model release approvals and deployment integration are not part of v184.5.

## Integration still required
1. Enable migration in isolated staging test DB and run HTTP/RBAC integration tests.
2. Connect correction ledger to effective field values in actual Inbox reads and downstream synthesis.
3. Add explicit approved-only insight projection to Command Centre, with dynamic invalidation and audit events.
4. Build reviewer UI, review queue, sampling and admin dashboard.
5. Implement persistent Gate 3 approvals and release evidence verification.
