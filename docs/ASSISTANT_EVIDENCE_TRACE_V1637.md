# v163.7 — Operational Assistant evidence traceability

Source cards now label **Cited in answer** only when their exact record_id occurs among the server-audited displayed citation IDs. Other cards are explicitly contextual, never implied to substantiate the AI's claims. The social source strip merges the selected records and featured subset without hiding non-featured evidence. Deduplication uses exact record IDs, not fuzzy content.

Action links for social evidence now require a newly generated answer in the current authenticated page session AND numeric source-post/campaign identifiers. Saved historical answers have no new-case shortcuts, even in cards, complementing v163.6's AssistantActionDesk guard. Existing backend casework source permission checks and officer confirmation remain mandatory. Formal/PDF references show citation/context provenance without making a legal validity or factual correctness assertion.

This is a presentation-only operational change: no database writes, API migrations, extra model calls or changes to restricted QA tools. Unit and frontend integration checks cover exact citation IDs, deduplication, non-featured evidence, and historical action-link suppression.
