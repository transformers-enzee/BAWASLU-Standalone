# v162.0 — Explicit saved-reply batch selection

Previous v161.9 batch audits always chose the first five eligible replies from
the history inventory, biasing reviewer choices and preventing investigation
of later or ineligible entries. This batch replaces the implicit first-five rule
with a capped, explicit checklist of at most five saved replies. An ineligible
reply may be selected so its reason can be documented without fetching its source.
Server validation remains all-or-nothing for duplicate selections and fail-closed
for other-user conversations, unauthorized evidence and stale source IDs.

Results now expose sanitized per-reason aggregate counts, not error internals
or source excerpts. UI emphasizes that findings are a convenience-selected set,
not a representative sample, confirmed model error count or measured accuracy.
No new paid AI calls, crawling, database mutations or source export.
