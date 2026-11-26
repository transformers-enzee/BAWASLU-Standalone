# BAWASLU v185.3 — Fix administrator campaign listing HTTP 500

### Incident
During first live manual QA, an authorized administrator received `Request failed (500)` on `GET /api/governance/qa/campaigns`. Render traceback on November 26, 2026:
`AttributeError: 'MonitoringCampaign' object has no attribute 'jurisdiction_type'`.
The UI incorrectly also displayed the empty campaign state because a failed load produced no campaigns.

### Fix
- Return real mapped `MonitoringCampaign` fields `id`, `name`, `province`, `regency_city`, instead of the nonexistent `jurisdiction_type`.
- Frontend clears stale options when refreshing and renders an explicit failed-load message, not the misleading `No authorized campaigns` message.
- Regression test constructs an actual SQLAlchemy `MonitoringCampaign` instance (instead of mocking arbitrary attributes) and verifies the authorized campaign list succeeds.
- No schema migration, officer data mutation, AI calls, or alteration of RBAC.
- Keep `BAWASLU_GOVERNANCE_QA_READ_ENABLED=true`, `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED=false`, `BAWASLU_GOVERNANCE_WRITES_ENABLED=false` on staging.

### Post-deploy live QA
1. Open /administration/governance-review as the authorized staging administrator. Confirm a campaign selector appears without HTTP 500.
2. Select a campaign with evidence. Verify Gate 1 sample and links, and Gate 2 count. If summary errors, check Render logs and fix before declaring QA pass.
3. Verify out-of-scope campaigns do not appear. Don't enable write flags.
