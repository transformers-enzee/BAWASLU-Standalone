# SmartRadar Intelligence Data Contract v1.0 — integration specification

Status: FOUNDATION ONLY. This branch defines reusable field groups and policy helpers; it does not yet expose an API, install database tables, wire frontend buttons, or change any live record.

## Raw -> Information: 10 assessment groups
- source_provenance: retain original immutable evidence and collection metadata
- content: language, transcription, clean summary and contextual completeness
- actors: named individuals, candidate identity, role and ambiguity
- geography_time: event location distinct from account location and collection time
- election_context: election type, stage, jurisdiction, competent authority
- violation_screening: preliminary allegation labels, legal-reference candidates, never an adjudicated violation by default
- narratives: targeted sentiment, stance, public concern and narrative
- evidence: corroboration, contradiction, source authenticity and verification status
- patterns: repeated posts vs distinct incidents, engagement and velocity
- triage: relevance, severity, urgency, priority, next action, review status

Use `FIELD_GROUPS` in backend/app/intelligence_contract.py as the machine-readable identifier list. Fields must be typed and assigned controlled vocabularies before API persistence. Unknown is a legitimate answer; no inference from missing metadata.

## Information -> Insights: 15 analytical variables
Issue frequency; trend velocity; geographic concentration; geographic spread; actor involvement; violation patterns; narrative evolution; sentiment movement; public concern intensity; evidence strength; jurisdiction relevance; risk severity; urgency/escalation; historical comparison; actionability.

Counts must use a documented denominator, date basis and deduplicated incident definition. Do not turn 50 copies of a post into 50 alleged incidents. Raw counts, verified incident counts and unverified mentions must remain separately labeled. An unreviewed urgent item can appear as a *preliminary warning*, never a verified finding.

## Human correction lifecycle (required before activation)
1. API authenticates officer, checks geographic scope and field-edit permission.
2. Officer proposes new value, writes justification and attaches evidence references.
3. Reviewer approves or rejects according to risk and role policy. Reviewer's identity cannot be trusted from request body.
4. Persist immutable source, AI suggestion, proposal, reviewer decision, actor IDs, timestamps, revision IDs and reason in an append-only log.
5. Serialize conflicts via transactional revision comparison, not a read-then-write guard alone.
6. Effective-value query resolves the latest approved field correction over AI prediction. Fresh AI evaluations cannot overwrite an approved correction.
7. Recompute dependent aggregates and invalidate caches using event/idempotency keys.
8. Show correction status and evidence in Inbox, Action Desk, reports and AI Assistant.
9. Training/export pipeline consumes only curated reviewer-approved labels, not every user edit.

**Critical implementation note**: `effective_value` and `require_expected_revision` are pure helpers, not security boundaries. RLS and/or server-side authorization must apply to every endpoint and record in addition to SQL transaction controls. Never trust a client-supplied reviewer ID.

## Proposed database entities (design; not migrated)
- `intelligence_field_assessment`: record ID, field, predicted value, confidence, evidence refs, model/prompt/taxonomy version, generated time
- `intelligence_field_correction`: assessment ID, field, proposed value, reason, proposed by, review status, reviewer, revision, timestamps
- `intelligence_field_audit`: append-only prior/new values, action, actor, evidence, transaction ID and timestamp
- `intelligence_incident_link`: post ID, incident cluster, link basis, review status
- `intelligence_insight_snapshot`: scope, window/date basis, metrics, supporting IDs, verification status and generation version

Avoid destructive migrations and do not assume these tables are absent in the newer staging image.

## Release gates
- Verify this branch against the actual source tag used by staging (currently a prebuilt GHCR image; the main branch is older).
- Add migrations and security policies to the real staging codebase, then test with synthetic records.
- Add field-level UI overrides in Raw, Inbox and Action Desk; provide recovery for excluded raw posts.
- Check permissions, unreviewed visibility, approval lifecycle, repeat AI runs, stale concurrent edits, cross-jurisdiction access and invalid source values.
- Verify aggregate changes, citations, exports and AI retrieval after an approved correction.
- Run full backend tests, frontend build, contract tests and staging UI acceptance tests.
- Deploy only a verified, immutable image digest/tag and report the exact deployed image after health and behavior QA.

No staging or production promotion is implied by committing this specification.
