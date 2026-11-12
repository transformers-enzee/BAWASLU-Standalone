# BAWASLU Phase 2 — Intelligence Integrity and Assessment QA (v147.4)

**Environment:** `architecture-v2-foundation-20261015` staging only.  
**Scope:** Phase 2 Tasks 1–3: saved Inbox source consistency, legal PDF references, social-platform policy screening.  
**Policy:** No paid AI assessments, no automatic takedowns, no legal verdicts, no database writes in the acceptance tests.

## Read-only Supabase data baseline (12 November 2026)

| Metric | Observed |
| --- | ---: |
| Captured social posts | 786 |
| Campaign/source links | 636 |
| Distinct linked posts | 616 |
| Saved assessment versions | 1,539 |
| Officer sentiment correction versions | 2 |
| Active uploaded PDFs | 1 |
| Officer-reviewed PDFs | **0** |

These are different denominators. Campaign links may overlap; assessment-version counts must **not** be displayed as unique posts or validated violations. The snapshot changes as new posts are crawled and officers review evidence. **No content or user-identifying information was extracted in this read-only audit.**

## Automated QA contracts

1. Saved relevant posts are grouped from the authorized **Intelligence Inbox**. Irrelevant posts do not enter Command Centre finding evidence. Repeated links are deduplicated without discarding stronger saved human review flags; the source ID, sentiment, platform and original URL are preserved.
2. Finding legal/policy assessments reuse the same authorized finding source list. The assessment reports distinct source IDs, deduplicated links, missing URLs/text and a mismatch against the finding support count instead of masking inconsistent counts.
3. Legal references are retrieved *only* from officer-reviewed legal-document types, filtered **before** the top-N retrieval limit. Citation keys include document ID and PDF page (`DOC-N-Pn`). The current validity of any law, legal element, statutory article or deadline is never assumed. The ordinary AI Assistant corpus remains independently accessible under existing authorization rules.
4. Platform policy references cover TikTok, Instagram, X, YouTube, Threads, Facebook, Reddit, LinkedIn and Telegram via provider-owned links. Local screening is source-text triage; it is not a platform decision, and adverse sentiment or ordinary political criticism is not a breach.
5. Reddit community rules are distinct from sitewide rules. Telegram private conversations are not automatically covered by its public-channel moderation rules. All platform policy *versions* remain marked unverified.
6. Provincial users cannot fetch another province's private PDFs or findings. Screens and exports must not authorize officer action or issue a takedown.

## Legal-content acceptance blocker

**No uploaded PDF currently has `OFFICER_REVIEWED` status.** The system can prove retrieval, authorization, citation and empty-result behavior, but it cannot demonstrate an actual officer-approved legal provision on live client data yet. A competent BAWASLU officer must supply or review current official regulations/SOPs, confirm document version and authority, and separately validate application to each incident. Do not mark legal-content acceptance complete from synthetic test fixtures.

## QA release acceptance

The code-release checklist is complete only when the GitHub backend tests, production frontend build, version contract, UI validation, PostgreSQL-security check, offline-assessment contract and Playwright browser suite pass **and** Render reports the exact `v147.4` commit live.

The client/legal acceptance gate is separate and remains open until current regulations and actual findings receive competent officer review.
