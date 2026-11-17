# v164.1 — Assistant exact Inbox source selection and compound-term relevance

Operational Assistant queries naming one or more real `INT-YYYY-NNNNNN` record IDs now resolve only those IDs in the authorized and filtered list. Matching record title, recency, or similar topics cannot substitute for a missing, unauthorized, or status-ineligible named record. If even one explicitly requested Inbox ID is unavailable, the combined v2 Assistant response is restricted to the existing no-matching-evidence flow; other social or PDF sources and general GPT cannot stand in for that missing named record. The maximum of ten requested formal IDs prevents silent partial comparison.

The formal evidence scorer also handles hyphenated versus spaced geographic terms as independent whole words, without reverting to substring matching or granting new access. It continues to rank selected source title and original content above metadata and preserves workflow filters.

The existing Social Listening exact-ID check and PDF page protections remain in place. No new database reads/writes, schema migration, additional provider call, casework changes, or admin QA screens. Automated tests cover exact and malformed IDs, missing IDs, validation restrictions, request limits, compound geographic wording, and an endpoint-level negative control.
