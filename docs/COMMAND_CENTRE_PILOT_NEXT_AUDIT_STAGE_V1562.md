# v156.2 — Pilot audit next-stage triage

Read-only pilot acceptance now uses the existing permission-filtered, at-most-200-transitions-per-case audit observation to identify the next unobserved stage. Stages are ordered according to the existing five-stage workflow. If 200 events are returned, the event history might be truncated: do NOT infer a definitive next missing stage or label missing evidence as absent. Instead show that the officer must inspect the full casework audit. When all five stages have audit evidence, show that human acceptance is still pending, never automatic completion.

Bilingual summary counts distinguish incomplete histories and next unobserved stages for the displayed preview only. None of these fields changes casework status, approval, legal findings, or the user authorization checks. No live writes, Supabase migrations, paid AI, or crawling calls.
