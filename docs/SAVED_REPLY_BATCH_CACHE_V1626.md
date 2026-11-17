# v162.6 — Scoped batch read reuse and citation coverage finding

The read-only saved-history inspection identified five replies with source cards but no bracketed citations. Individual and batch audit now report SAVED_CARDS_WITHOUT_DISPLAYED_CITATIONS separately; this is not a confirmed factual or legal defect.

The five-reply batch previously repeated expensive permission-filtered Social Listening and formal Inbox reads for every reply. A fresh per-request dictionary now reuses those already-authorized inventories within a single user's batch, never across requests or users. Every record ID must still be present in the scoped inventory; unlisted IDs fail closed. The batch has no new model calls, database writes, or vendor credit consumption. Neither lower staging latency nor reduced Supabase egress is claimed until directly measured.
