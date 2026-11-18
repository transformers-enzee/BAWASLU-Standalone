# BAWASLU v168.7 — Cross-module persisted-link integrity

The national-administrator-only module acceptance inventory now reports separate counts for four persisted handoff links: Social Listening → campaign source, Social Listening → promoted Inbox item, Assistant knowledge chunks → PDF, and officer report → parent case. A broken link is flagged as REVIEW_REQUIRED and returns only counts, not source URLs, names, texts or IDs.

This is a concrete database-integrity check, **not** proof of chart accuracy, human officer approval, AI answer grounding, or client acceptance. The six end-to-end UAT gaps remain unverified until tested at the workflow level. No provider calls, new database queries beyond the existing single counts snapshot, or application-data writes are required for the inspector. SQLite regression fixtures create missing links intentionally; the connected Supabase database is never changed.
