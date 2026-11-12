# BAWASLU v150.2 — Sentence-level legal PDF attribution

## Gap fixed
The v150.1 article checker joined all cited PDF pages into one shared pool. An AI answer could cite the wrong page for "Pasal 21" but still pass the text-presence check if a different cited PDF page included Pasal 21 elsewhere.

## Implementation
- Retain v150.1's whole-answer list of legal articles absent from all actually cited PDF pages.
- Additionally split the raw generated answer into punctuation/newline-bound text spans, then associate explicit DOC-ID citations with article mentions in the same sentence.
- Where a named article is absent from that sentence's cited PDF page excerpts, return the article and cited page IDs as a review mismatch.
- Add a short user-visible article warning in the normal AI Assistant when either global or sentence-level mismatch exists, and set existing legal-uncertainty diagnostic to REVIEW_REQUIRED.
- Do not treat social cards, uncited PDFs or inaccessible invented references as proof of an article.
- No legal article text match is a substantive legal verification. Sentence pairing is heuristic; complex multi-sentence legal reasoning still requires human review.

## Constraints
Staging branch architecture-v2-foundation-20261015, sequential build v150.2; no DB writes, Supabase migration, paid AI, crawling, automatic casework or legal decisions. Automated tests cover reversed page attribution, correct attribution, unrelated social evidence, uncited claims and invented page IDs.
