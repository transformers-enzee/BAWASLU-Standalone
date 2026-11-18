# v169.3 — Inbox / Command Center assessment selection reconciliation

This change uses the same authoritative evidence ordering as Inbox: completed classifications precede provisional PRISM rows, with assessment version and row ID as deterministic tie-breakers. A window function returns only one classification per campaign/source for Command Center's period-scoped KPIs.

The most recent assessed evidence and geographic signal sections reuse that same ordering, preventing superseded classifications from leaking into executive summaries and regional signals.

Synthetic SQLite regression checks cover equal-version conflicts, newer PRISM_PENDING_OPENAI placeholders, and preliminary PRISM_OPENAI_TOPIC_CLASSIFIER rows. No live assessment data or officer decisions are modified. A green Render build does not substitute for backend pytest/CI verification.
