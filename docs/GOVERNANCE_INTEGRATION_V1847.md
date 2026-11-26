# BAWASLU v184.7 - governance staged integration and database verification

**Database operation**: An additive, named Supabase migration created `governance_field_corrections` and `governance_insights` in the existing BAWASLU project. No existing rows were updated or deleted.

**Verified**: both new tables are RLS-enabled, have zero policies, and `anon` / `authenticated` do not have table SELECT privilege. This is intentional: all access must go through the authenticated app backend. The remote Supabase migration registry and the project's existing Alembic version table are separate; keep Alembic version reconciliation explicit before ever enabling automatic upgrades.

**Code integration**:
- Officer corrections only accept strongly validated `sentiment` and `relevance` values. Unsupported fields remain handled through pre-existing review flows.
- The existing Inbox response can attach `governance_effective_preview` for its already-visible scoped records, using a single bounded batch query. Existing sentiment and Inbox eligibility are preserved until both review systems are reconciled.
- Command Centre can return `governance_approved_insights` as a separate read-only list that rechecks source freshness and publication gate. It does not modify existing alert or indicator calculations.
- Both adapters remain OFF by default: `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED` must be set intentionally after API integration QA. Governance persistence also requires `BAWASLU_GOVERNANCE_WRITES_ENABLED`.

**Still required**: independent review of effective-value conflicts with legacy sentiment records, full relevance eligibility and count reconciliation, authoritative approval publication workflow, human-facing review UI, persistent Gate 3 approvals, migration reconciliation, and live scoped API tests with authorized officer roles. Do not enable governance writes based only on successful Docker build.
