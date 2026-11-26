# SmartRadar v184.9 | Controlled pilot activation and audit integrity

**Scope:** staged governance read/write readiness, not production rollout. Two governance tables already exist in BAWASLU Supabase and contain no officer trial records as of release preparation. No schema changes or paid AI requests in this batch.

## Corrected blocking issues
1. **Read-only access separated from write access.** GET governance assessment, history and approved-only feed APIs require `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED=true`. They do not require `BAWASLU_GOVERNANCE_WRITES_ENABLED`.
2. **Write-boundary pilot isolation.** All three governance write operations now require (a) `BAWASLU_GOVERNANCE_WRITES_ENABLED=true`, (b) `BAWASLU_GOVERNANCE_PILOT_MODE=staging`, and (c) a strict `BAWASLU_GOVERNANCE_PILOT_CAMPAIGN_IDS` allowlist (1-10 distinct positive integer IDs). Absent/malformed values deny all writes.
3. **Watchlist exclusion.** A watchlist-only link cannot be used as ordinary campaign evidence for a governance approval or correction.
4. **Dual-ledger conflicts.** A governance sentiment correction which contradicts the legacy officer sentiment value blocks approval and approved-only publication, and is surfaced in the review queue as `RESOLVE_REVIEW_CONFLICT`.
5. **Append-only actor audit.** Governance field correction, insight proposal and approval/rejection append `AuditEvent` in the same database transaction as their action. No retroactive changes to source or original AI assessment rows.
6. **Administrator readiness security.** PostgreSQL table checks are scoped to `public`; readiness separately displays read/write flags and pilot allowlist counts.

## Next acceptance step
- Deploy v184.9 to Render staging with both governance flags OFF.
- Run administrator readiness read-only, then enable **only** `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED=true` on staging after successful smoke tests. Keep writes OFF.
- Exercise authorized/unauthorized scoped read-only officer data. If it passes, choose a small dedicated test campaign and perform a controlled write pilot with two distinct officer accounts.
- Only then request human-facing manual QA from the user; present simple UI steps and avoid exposing backend workbench.

This change does not replace legacy Inbox sentiment corrections or preliminary Command Centre indicators. The official approved-only publication model still requires operational validation.
