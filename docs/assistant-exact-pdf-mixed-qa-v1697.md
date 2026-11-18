# v169.7 — exact PDF page integrity across mixed AI Assistant questions

Exact named PDF pages in any response mode must all resolve to currently authorized indexed page excerpts. The main Assistant endpoint stops before retrieving alternative Social Listening or formal records when a requested page is missing, withdrawn, inaccessible or beyond the six-page bounded selection limit. It returns a deterministic no-matching-evidence response; no paid AI provider call is made.

Existing PDF-only paths and citation audit remain intact. Added synthetic tests for partial-page selection, foreign document substitution, invalid citation types, and mixed social/PDF fallback. No staging database mutations.
