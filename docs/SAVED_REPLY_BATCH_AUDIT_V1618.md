# v161.8 — bounded batch auditing of owned saved Assistant replies

The previous v161.7 interface audited one stored reply at a time. v161.8 adds
`POST /api/assistant-evaluation/saved-reply-batch-audit`, accepting 1–5 exact
saved reply selections from a single authenticated user. The operation reads
user-owned saved conversations using a single bounded thread query, checks the
original adjacent question and full saved source-card scope, reopens each
selected source against current permissions, then runs the existing deterministic
answer audit. Each reply explicitly returns AUDITED, INELIGIBLE,
SOURCE_UNAVAILABLE or UNAVAILABLE. Missing, revoked and stale sources never
count as audited replies; other-user IDs cannot expose whether a thread exists.

The Assistant QA panel offers a one-click audit for the first five eligible
saved replies, with per-answer statuses, warning-category occurrence counts and
an optional action to capture those candidates in the local session register.
The batch provides no model inference, crawling or database mutation. It does
not establish original model provenance (saved threads are user-editable),
ground-truth answer accuracy, legal applicability, or client acceptance.
No raw saved answer text or evidence excerpt appears in audit results.
These batch results are a bounded convenience sample, not a statistical estimate.
