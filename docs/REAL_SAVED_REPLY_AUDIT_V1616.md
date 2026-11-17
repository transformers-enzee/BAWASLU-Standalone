# v161.6 — permission-scoped replay audits of real saved Assistant replies

The previous QA workflow required reviewers to regenerate or manually paste Assistant responses. The database read-only inventory on 17 Nov 2026 found 22 stored threads containing 49 Assistant replies; 48 had saved source cards. These are historical totals across accounts, **not current accessible replies for an individual officer**, and do not establish authenticity or accuracy.

New endpoints:
- GET /api/assistant-evaluation/saved-reply-candidates: lists only the authenticated user's own saved Assistant turns with bounded metadata and eligibility/reason codes, omitting question text, answer text and source excerpts. Listing is not source permission approval.
- POST /api/assistant-evaluation/saved-reply-audit: selects one exact saved assistant reply and its adjacent user question, maps both modern `record_id` and historical social-card `id` formats, reopens the entire saved card scope through live authorized Inbox, formal intelligence and exact active PDF page readers, and runs the existing read-only mixed-evidence QA. Any unavailable or unauthorized source rejects the full audit. No silently truncated source sets; at most 12 records.
- The Assistant evaluation UI provides a voluntary "Find my saved replies" control and per-answer read-only audit, with sanitized warning candidates and local JSON issue capture. No new model calls or crawling.

Limitations: saved conversations are user-editable and are **not authenticated model-run proof**; the QA compares the stored text with current authorized evidence (which can have changed since generation), and is not a human accuracy evaluation or official legal determination. Statuses and source IDs only are emitted, no raw texts in audit responses or issue exports, no DB mutations and no AI credits.
