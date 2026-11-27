# BAWASLU v186.3 — Human Gate 1 feedback governance and Gate 2 handoff readiness

Environment: staging branch `architecture-v2-foundation-20261015`. No operational database migration or direct Supabase table access added. Initial Render deployment must keep `BAWASLU_INBOX_GATE1_WRITE_ENABLED=false`; production is untouched.

## Operational separation

**Social Listening (raw evidence) → Human Gate 1 (reviewed information) → synthesis / proposed insight → Human Gate 2 (independent insight approval) → Command Centre**. Human Gate 3 governs offline QA labels, AI evaluation and any later model promotion. None of these gates should substitute for another.

The current GovernanceInsight system already supports separately proposed and approved insights, with independent proposer and approver requirements. v186.3 DOES NOT invoke that system's create/approve/publish routes. The Gate 2 handoff preview is **read-only**: `CANDIDATE_FOR_INSIGHT_DRAFT` means only that the current information snapshot meets preliminary drafting prerequisites, not an insight proposal, legal verification, or permission to publish.

## New server endpoints (authenticated and scoped)

- `GET /api/inbox/human-review/campaign/{campaign_id}/source/{result_id}/gate2-readiness`: read-only current assessment and officer review snapshot, status and blockers. Requires campaign and geography authorization. Blockers include missing/pending assessment, election relevance unconfirmed, missing source trace, stale/absent Gate 1 information review, and conflicting sentiment review ledger. Returns false for proposed insight, legally verified allegations, publication, and model training regardless of readiness.
- `GET /api/inbox/human-review/campaign/{campaign_id}/source/{result_id}/feedback`: most recent 40 audited officer field corrections/restorations, no raw social content or training exports. Each item shows old/new effective value, officer ID, reason, current/superseded state, current Gate 1 verification, latest governance disposition and its revision.
- `GET /api/inbox/human-review/campaign/{campaign_id}/feedback?limit=20&cursor=...`: authorized paginated feedback candidates with a bounded maximum scan of 200 entries per request. Out-of-scope posts do not appear; counts refer only to the returned page, not campaign-wide AI quality.
- `POST /api/inbox/human-review/campaign/{campaign_id}/source/{result_id}/feedback/triage`: append-only `Gate1FeedbackDecision` audit event, independently versioned per correction event. Requires the existing strictly synthetic QA campaign + source write gates **AND** administration + human-validation + officer edit permissions. A current source fingerprint and optimistic decision revision are required, under the same source-row lock as normal corrections. Choices: `ACCEPT_OFFLINE_EVALUATION`, `REJECT_OFFLINE_EVALUATION`, `NEEDS_RECHECK`. Acceptance additionally requires the selected correction still effective and the full information snapshot currently `OFFICER_VERIFIED`. Stale decisions fail HTTP 409. All events retain actor, reason, revision, source digest, assessment version and flags marking training and publication disabled.

**Acceptance for offline evaluation is not authorization for AI training.** No model export, retraining call, fine-tuning API, model promotion or deployment is launched. A later Gate 3 governance control is required.

## Officer-facing UI

- Optional, collapsed-by-default **View officer correction feedback queue**, with batch browsing and direct source selection.
- Per-source **Check insight-draft readiness** shows blockers and expressly states that an independent Gate 2 approval remains mandatory.
- Per-source **View correction feedback** displays lineage and current/superseded dispositions. Only a permitted pilot administrator sees the offline triage controls; ordinary officers can read the authorized history but cannot write.
- Existing evidence detail, officer correction/restore workflow, audit panel, review-status filters, and read-only pilot preflight remain available. Selecting a new record discards pending previews to avoid mixing records.

## QA

- SQLite unit/integration: blocked vs ready handoff, existing GovernanceInsight row count remains zero, append-only feedback decisions and stale revision conflicts, Supabase-independent scope checks, old correction invalidation, read-only viewer denial, paginated scoped feedback, and training disabled.
- Ephemeral PostgreSQL + real Chromium: initial blocker; correct relevance and sentiment; reviewer verifies saved information; readiness becomes candidate-for-draft (not publication); admin accepts current sentiment correction for offline evaluation; later correction invalidates its eligibility; restore relevance; audit history shows new revision; viewer role and watchlist source denied. Independent post-browser SQL audit confirms exact original evidence, three relevance versions, two sentiment corrections, five field/review events plus one offline feedback event; no published intelligence.
- Full existing backend and UI regression, Supabase security check and verified staging Docker image build must pass before handoff.

## Deployment and pilot safeguards

1. Keep `BAWASLU_INBOX_GATE1_WRITE_ENABLED=false` on shared Render staging. No new environment flags required for read-only previews. No live data corrections are part of this release.
2. Test the new read-only panels on authorized, existing evidence after staging deploy; the special QA campaign remains Draft with zero evidence and `NOT READY · SAFE BLOCK`.
3. No human write pilot may be run against BAWASLU's shared Supabase database. Isolated PostgreSQL CI remains the write acceptance environment.
4. Human Gate 2 publication controls are **not** exposed inside Gate 1. Human Gate 3 AI-learning and promotion remain separate, explicitly governed workflows.

Version commit convention: v186.3 (one bulk commit). Next QA milestone: review officer usability on real non-QA sources in read-only mode, with no edits.
