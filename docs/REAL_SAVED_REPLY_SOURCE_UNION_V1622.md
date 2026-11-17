# v162.2 — Real historical saved reply citation scope repair

Read-only aggregated Supabase audit (17 Nov 2026) found 49 historical Assistant
replies, 43 with bracketed citation IDs, and 11 of those with at least one
displayed source ID missing from the saved response's contextual card shortlist,
after normalizing legacy source identifier formats. Union sizes for these cases
range from 13–20 distinct IDs. This is NOT a confirmed model error rate:
contextual cards are an excerpt of selected evidence and citations are distinct.

The old replay workflow reauthorized only saved cards, risking incorrect
unavailable-citation warnings even for authorized cited IDs. v162.2 now forms
the bounded union of saved card IDs and all displayed source IDs in the reply,
deduplicating without assigning cited-only source IDs any automatic authority.
Every ID still has to be reauthorized against the user's *current* authorized
Social Listening, formal Inbox, or exact PDF page scope. If any ID is missing,
revoked, inaccessible or malformed, the entire replay fails rather than
substituting, skipping or fabricating evidence. Saved cards stay capped at 12;
the combined historical replay scope is limited to 20 IDs. Above 20 is explicit
ineligibility. Existing 12-unique-visible-citation limit in the normal Assistant
response grounding remains unchanged; this feature is only for QA replay.

The read-only mixed audit allows at most 20 requested IDs to support the same
replay mechanism. Existing exact PDF page retrieval retains its independent
12-page hard cap; over-limit PDF access still fails closed. The private local
QA warning register accepts the expanded source scope without exporting raw
saved messages or original excerpts.

Passing the deterministic audit does not verify source truth, legal applicability,
independent model provenance, human-rated accuracy or BAWASLU acceptance.
No new paid AI calls, crawls or database mutations.
