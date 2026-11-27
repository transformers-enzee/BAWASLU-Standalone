# BAWASLU v185.8 — Human Gate 1 field corrections and review decisions

Architecture baseline: BAWASLU SmartRadar Data Intelligence Governance Architecture v1.0 (25 Nov 2026), pp. 4–9.

## Bulk batch
- Add dedicated Gate 1 officer endpoints for relevance/sentiment corrections, information review decisions, version history, and restoration of earlier field values.
- Keep existing AI assessment and officer sentiment tables as the respective effective-value sources; record a new version on every accepted change.
- Preserve original provider payload, original saved evidence, and all historical revisions.
- The information review status (OFFICER_VERIFIED / NEEDS_REVIEW / HELD / EXCLUDED) is an append-only AuditEvent for campaign + source. After a newer field correction the decision is marked REVALIDATION_REQUIRED instead of silently remaining verified.
- Never equate a corrected field or officer-reviewed information with verified legal allegations.
- Keep ordinary Inbox, its metrics, and Command Centre publication behavior unchanged; existing correction models already determine the effective relevance and sentiment.
- No paid AI calls or training; officer corrections become review data, not automatic model learning.

## Access and rollout
- All Gate 1 routes require the existing read flag and authenticated campaign/geography-scoped source access.
- Writes additionally require all of:
  - `BAWASLU_INBOX_GATE1_WRITE_ENABLED=true`
  - `BAWASLU_INBOX_GATE1_PILOT_MODE=staging`
  - an explicit numeric campaign ID in `BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS` (max ten, no wildcard)
  - `human_validation` AND `edit_intelligence`, plus the existing campaign edit check
  - a minimum ten-character explanation, accepted label, and current revision token
- Leave the write flag OFF for initial v185.8 staging deployment. Do not enable it on production.
- A stale correction or review decision fails with HTTP 409; unauthorized or out-of-geography source reads/writes fail closed.
- In-place source modifications and correction deletions are not permitted. 'Restore' writes a new version with a restored value, preserving earlier decisions.

## Data and Supabase
- Uses existing `evidence_assessments`, `evidence_reviews`, `officer_sentiment_corrections`, and `audit_events` tables.
- No schema migration, raw source rewrite, or Supabase RLS change.
- All actions run through the server-side authenticated SQLAlchemy connection; no direct browser access to privileged Supabase tables or credentials.
- Relevant per-source audit history is limited to the most recent 80 events in the officer UI; stored history remains unchanged and can be exported via existing governance operations.

## Automated QA
- Unit/in-memory SQL tests for source preservation, field versions, stale-update rejection, restore-as-new-version, decision staleness, RBAC/pilot protection and client action bindings.
- Full backend regression, staging security workflow, officer UI acceptance, Playwright, and GHCR verified image CI.

## Post-release/manual QA gate (before enabling writes)
1. Deploy v185.8 with Gate 1 write flag still FALSE. Repeat the v185.7 read-only smoke check.
2. Administrator: select one disposable, authorized pilot campaign and evidence record; validate its source/assessment versions in Supabase and confirm a recovery path. Keep production data untouched.
3. Set the staging-only write flag, mode and allowlist for that campaign, then verify permitted and forbidden roles/geographies.
4. Correct relevance and sentiment with a distinct reason; confirm new effective values and audit entries without overwriting original source.
5. Try a stale expected revision and verify a conflict. Restore a prior relevance value; confirm a new revision and complete history.
6. Record OFFICER_VERIFIED, then correct a field; confirm REVALIDATION_REQUIRED. Verify Command Centre remains unchanged until Gate 2 approval, and no model training occurs.
7. Disable the write flag after acceptance until administrative rollout policy is signed off.

No manual write QA is required before the image is built and deployed read-only.
