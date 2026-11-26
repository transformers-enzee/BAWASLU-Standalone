# SmartRadar Human Governance - v184.3 foundation

**Staging-only architecture contract.** This batch introduces deterministic three-gate decisions and offline tests. It does **not** claim that production write routes or Command Centre publication endpoints have been wired to these functions.

## Data flow

1. Social listening raw records are preserved unchanged. Cleaning creates normalized derivatives and separately tracks exceptions.
2. AI-assessed election-relevant records are visible in Intelligence Inbox without falsely claiming officer verification. Ordinary candidate/political-party conversations are in scope even without suspected violations.
3. Gate 1: selective officer review, mandatory for consequential claims or uncertain source classifications. Review overrides are field-level and append-only; irrelevant/excluded results remain available for audit and false-negative sampling.
4. AI may synthesize trends from permitted data, but must label unreviewed inputs and avoid verified conclusions.
5. Gate 2: a reviewed insight requires an explicit approving officer, immutable approved revision, traceable evidence, a declared analysis scope and fresh source revision before publication to Command Centre.
6. Gate 3: AI learning release requires validated correction examples, held-out evaluation, regression results, security check, version pinning, administrator authorization.

## Write-boundary integration checklist

- [ ] Attach Gate 1 to scoped Inbox assessment/override persistence and exception queue.
- [ ] Store provider / AI / officer / effective values separately; audit reviewers, reasons, model version, timestamps, revisions.
- [ ] Attach Gate 2 to actual Command Centre insight publish/update API; enforce approver RBAC and per-jurisdiction ACL transactionally.
- [ ] Invalidate published findings if supporting record revisions or officer corrections change.
- [ ] Persist Gate 3 release attestations and enforce them before AI runtime/prompt/model rollout.
- [ ] Monitor sampling precision/recall, false-negative samples, review backlog, evidence traceability and model drift.
- [ ] Add end-to-end API authorization and staging Supabase persistence tests before promoting any enforcement to production.

All three gate functions are **pure helpers**: they never perform database writes, issue external requests, authorize paid AI calls, or create legal determinations. Caller must authorize access, persist append-only audit records, and fail closed at a real API write boundary.
