# BAWASLU v150.8 — Mixed social allegations, PDF law and officer actions

This batch targets actual inconsistencies in multi-source Assistant responses, without any new AI run.

1. Citation reconciliation had a hidden cap mismatch: only the first twelve distinct source IDs were recorded in metadata, while later valid IDs were left visibly printed and could be mistakenly treated as audited. The audit now removes extra unique citations from the displayed answer, retains repeat uses of the first twelve, exposes an overflow count, appends a caution and marks citation grounding REVIEW_REQUIRED.
2. A definite guilt statement could be hidden by an uncertainty qualifier in the preceding introductory clause of the same sentence, e.g., "Although the allegation is unverified, the candidate is guilty." The categorical-language detector now separately checks the independent clause following a recognized concessive lead (English and Indonesian). Reported speech and question/hedging safeguards remain.
3. Expose distinct review-reason codes for assertive legal outcomes, enforcement instructions, article attribution errors, unreviewed cited PDFs and citation-integrity issues. Add a concise combined-review warning to the normal officer view if multiple issues occur together. This status never grants legal authority, casework approval, or human review acceptance.

Regression suite: seven deterministic tests for cross-module social/PDF answers, concessive allegations, quoted language, citation overflow, retained duplicates and mixed legal warnings.

All assertions are about deterministic triage, not correctness of legal conclusions. Staging branch only; no database changes, model API calls, crawls or automated legal enforcement.
