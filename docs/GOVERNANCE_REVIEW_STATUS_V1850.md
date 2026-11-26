# v185.0 — Read-only officer governance review status

## Purpose
An internal administrator-only, concise QA entry point in Administration. Unlike the synthetic assessment workbench, it reads actual authorized campaign review records and source-current publication blockers.

## Server-side APIs
- `GET /api/governance/readiness`: existing administrator-only schema/RLS and read/write flag status. Available even when read integration is disabled.
- `GET /api/governance/qa/campaigns`: **read-only flag required**; both administration and view_intelligence permissions required; campaign geography filtered using `allowed(p,c)`; max 80 rows.
- `GET /api/governance/qa/campaign/{id}/summary`: **read-only flag required**, same RBAC, jurisdiction check; uses existing source-current Gate 2 review queue; max 30 insight cases.
- No command executes a paid AI request or modifies officer/source records.

## Frontend
- `/administration/governance-review`: permission-gated page linked only from Administration for authorized officers; hidden from external/ordinary navigation.
- It shows schema readiness, whether read-only or pilot-write flags are enabled, campaign-specific cases, evidence freshness and blockers.
- It contains no correction or approval buttons.

## Manual QA gate
Deployment alone does not authorize manual QA. With database checks validated, next perform controlled staging read-only flag activation, verify API role/geography boundaries and test data, and only then invite an officer to validate the simple page. Staging write flags must remain disabled until a separate controlled two-officer pilot.

## Version convention
After v184.9, next release is **v185.0**.
