# BAWASLU Phase 2 — AI Assistant Grounding Integrity (v148.3)

**Environment:** staging only (`architecture-v2-foundation-20261015`).  
**User goal:** Improve trustworthiness of AI Assistant answers using the existing authorized social/InBox and PDF knowledge corpus, without rebuilding modules or spending API credits on QA.

## Verified baseline

The connected Supabase database currently contains **1 active PDF**, **0 officer-reviewed PDFs** and **23 PDF chunks**. This provides a retrievable test corpus but no approved legal-document authority. There are also no real officer casework records yet. These are read-only observations and must not be treated as a legal acceptance test.

## Bulk implementation

1. **Deterministic citation reconciliation.** The Assistant post-answer audit matches each displayed bracket reference (INT, SOCIAL, DOC-page) against its **currently authorized, selected** evidence. Unknown bracket references are stripped from the displayed answer; structured model citation IDs that were never printed are not counted.
2. **Source cards versus citations.** The response reports distinct `cited_count` and `source_card_count`. When citations are absent, available cards are explicitly labelled contextual, not supporting proof. Source evidence or source relevance is **not** verified true by a citation match.
3. **PDF review guardrails.** For PDF-guidance answers, the audit warns when a selected PDF is unreviewed, even if the response omits its citation. Legal questions with no cited officer-reviewed legal guidance disclose the missing legal authority. Even reviewed PDF material is **not** a verification of current statutory validity, amendments, repeal or official legal effect.
4. **Visible provenance.** AI Assistant now displays a compact citation-integrity line on answers returned through the existing chat API. No extra navigation module or duplicate document store.
5. **Offline automated QA.** Test cases exercise invented citations, missing displayed citations, valid page IDs, reviewed/unreviewed docs, no-evidence legal questions, repeated IDs and a real Playwright chat rendering with contextual source cards. QA never calls a paid model or modifies user data.

## Explicit limitations

- The check validates **source identifiers and declared document review status**, not the semantic correctness of each generated claim. An authorized source can be unrelated to a claim; an officer must still verify context.
- A PDF marked `OFFICER_REVIEWED` is not independently verified as current legislation.
- The current knowledge corpus has no officer-reviewed PDF and cannot support client-ready legal conclusions. The Assistant should use explicit qualifications instead of inventing legal authority.
- Existing user-initiated AI Assistant questions can still call the configured AI model; **these automated QA tests do not.**
- PDF uploads, officer approvals, social evidence and permissions remain unchanged. No database migration, live data writes, takedown or external legal action.

## Release checks

Backend tests (including `test_assistant_grounding_v1483.py`), frontend production build contract, browser Playwright test, authorization/security and offline-contract checks, sequential v148.3 version, and exact GitHub-commit Render staging status.

## Separate open acceptance gates

1. A competent authorized officer must approve current BAWASLU legal PDFs and verify their effective dates, amendments and authority.
2. A real authorized officer must complete source-linked casework and independent approval; synthetic fixtures do not count as client sign-off.
3. Subject-matter experts must evaluate AI Assistant answer **quality** against a reviewed, representative evaluation set. Passing citation-integrity checks is not a measured legal or classification accuracy score.
