# BAWASLU v185.5 — Human Gate 1 inside Intelligence Inbox

## Why this is necessary
Administrator Human Review Status linked directly to /inbox?campaign_id=<id>&result_id=<id>. The ordinary Inbox intentionally displays only assessments labeled RELEVANT/HIGHLY_RELEVANT. Clicking an unassessed or IRRELEVANT post therefore loaded an empty ordinary Inbox instead of the original source.

## Implemented
- Same operational URL /inbox, with an explicit **Needs Human Review** officer lane: `?gate1=1&campaign_id=<id>&result_id=<id>`.
- Existing ordinary Inbox remains relevant-only, with its metrics and navigation unchanged; an entry button opens the new lane. No new separate officer page is introduced.
- Separate source-scoped, permission-checked, read-only endpoints `/api/inbox/human-review/campaigns`, `/campaign/{id}/sample`, and `/campaign/{id}/source/{id}`. Exact evidence lookups use the existing `_source` helper, which requires campaign link, excludes WATCHLIST_ACCOUNT-only records, and checks geographic source scope.
- A balanced bounded sample shows unassessed, uncertain, excluded and relevant election posts, not only violation signals.
- Source preview includes saved text and original URL, saved relevance and sentiment, officer sentiment precedence, latest review decision, and assessment version. No external fetch, no paid AI, no original source alteration.
- Authorized officer relevance corrections reuse the **existing** `campaignAssessmentCorrection` audited action, not a competing ledger. Corrections require a saved assessment, existing `_editable` permissions, minimum 10-character rationale, and a separate opt-in write switch. An unassessed source without saved assessment is visible but read-only; do not misrepresent it as assessed.
- The admin QA page link now opens this officer review lane rather than the relevant-only Inbox.

## Safety and rollout
- New feature flags default OFF:
  - `BAWASLU_INBOX_GATE1_READ_ENABLED=false`
  - `BAWASLU_INBOX_GATE1_WRITE_ENABLED=false`
- Deploy to Render staging with flags OFF. Enable READ only after verifying startup. Keep WRITE off for first manual QA.
- Admin QA flag may remain enabled. General `BAWASLU_GOVERNANCE_INTEGRATION_ENABLED` and `BAWASLU_GOVERNANCE_WRITES_ENABLED` must stay OFF; Gate 2 approved-only publication remains separately controlled.
- Before enabling review writes: run role- and scope-specific acceptance tests; confirm a correction creates a versioned `EvidenceAssessment` and an audit event, and does not publish official insights or train AI.
- No schema migration, paid model calls or production rollout in v185.5.
