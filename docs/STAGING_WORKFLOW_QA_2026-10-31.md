# BAWASLU staging: cross-module QA and data-integrity audit
Audit date: 2026-10-31 (Asia/Kuala_Lumpur)
Branch: `architecture-v2-foundation-20261015`
Target build: `115.7`
Scope: staging-only, read-only Supabase inspection, mocked external provider unit/integration tests, GitHub Actions and Render build/deploy verification.

## Required end-to-end lineage
1. Legacy keyword crawl or Discover -> Social Listening Captured Posts -> campaign evidence where `match_method != 'WATCHLIST_ACCOUNT'`.
2. Campaign evidence -> bounded AI assessment -> latest assessment version -> Intelligence Inbox for AI-assessed relevant posts -> Command Centre indicators / officer actions.
3. Watchlist registered candidate profile -> separately requested, budget-capped own-account collection -> `WATCHLIST_ACCOUNT` evidence -> candidate Own Posts only.
4. Candidate Mentions by Others -> matching posts that already exist in the selected campaign's Captured Posts; never a secondary crawl or Inbox global feed.
5. Officer decisions remain append-only, historical source records unchanged. Indicators are never legal determinations.
6. The campaign dashboard, AI batch previews, assessments, Inbox, Command Centre and candidate suggestions must exclude `WATCHLIST_ACCOUNT` rows from ordinary capture denominators.

## Read-only Supabase snapshot
- Campaigns: BAWASLU **298** keyword/Discover captures; Test **58** captures + **12** separately registered-account posts; Pemilu **26** captures. Total campaign-capture links: **382**, account-only links: **12**.
- Stored social results: **564** (includes historical unlinked records). **170** results are not linked to a current campaign; do not delete or silently attribute them.
- Data quality of all stored results: **9** missing text, **1** missing canonical URL, **16** distinct URLs duplicated (including one URL present three times). These issues are mostly historic or unlinked, not automatic permission to delete evidence.
- BAWASLU campaign has **17 duplicate-candidate URL rows** (rows participating in duplicate URL groups). Keep source IDs and existing assessment history until reviewed; future ingest should dedupe by normalized canonical URL, subject to provenance.
- Latest saved relevance: BAWASLU 214 RELEVANT, 17 IRRELEVANT, 3 UNCERTAIN, **64 UNASSESSED**; Test 21 RELEVANT, 8 IRRELEVANT, **29 UNASSESSED**; Pemilu 23 RELEVANT, 3 IRRELEVANT.
- Latest sentiment unresolved (not POSITIVE / NEUTRAL / NEGATIVE): **15** Test and **8** Pemilu = **23**. Do not manufacture NEUTRAL for genuinely unknown posts. Source sentiment and AI-screening status are separate signals.
- AI jobs: 44 durable assessment jobs all COMPLETED; an absence of a pending job is not proof of a completed assessment.
- Intelligence Inbox manual entries: **7**, including entries previously marked validated but with `verification_status=UNVERIFIED`. The dataset includes unrelated foreign news and consumer technology sources. Flag for **officer review / test-data isolation**, not automatic deletion or rewriting human decisions.
- Candidate Gibran: one registered Instagram account with **12** fetched Own Posts; automatic scheduled collection remains disabled. `WATCHLIST_ACCOUNT` rows must not inflate Captured Posts or command-centre coverage.
- Historical Render logs showed SQLAlchemy connection pool timeouts on 2026-10-30. Current SQL connection snapshot showed 7 idle and 1 active connections; this does not establish the timeout is permanently resolved.

## Automated gates
- CI Python regression suite (mock provider; no credits), React production build, prototype script syntax, Watchlist 16-mention and 58+12 scenario, candidate duplicate and attribution guards, regional access, saved assessment provenance, and source-history preservation.
- Docker pre-deploy Python tests, Render deployment reaches Live.
- New `115.7` regression checks verify Watchlist own-account posts do **not** appear in campaign dashboard counts, sentiment AI batch previews, AI backlog, candidate recommendations, or Command Centre captured activity/alerts.
- The audit itself must never run paid SocialCrawl/OpenAI requests, truncate source records or auto-modify officer review outcomes.

## Unclosed work (not falsely marked DONE)
1. Manual forensic / human quality calibration of 93 `UNASSESSED` relevance labels and 23 unresolved sentiment labels; ask for separate capped AI run approval before spending model credits. Some labels originate in earlier provider imports; validation must compare text with assessment.
2. Decide treatment of duplicate canonical URLs with review of provenance, versioned assessments, and source IDs before any migration or deduplication.
3. Investigate historical pool timeouts under a representative authenticated concurrent user load; no soak test was executed with production credentials.
4. Audit 7 seeded/manual Intelligence Inbox records for non-BAWASLU examples. Preserve officer decisions, but identify test data and isolate it from client acceptance if needed.
5. A genuine authenticated browser E2E with national and provincial test accounts remains unverified; offline UI mocks and build checks are not that test.
6. No claim of 100% model accuracy without labeled baseline, independent adjudication, and false-positive/false-negative review.

This is a QA snapshot and acceptance record, not a declaration that all data or model decisions are correct.

## Full-suite escalation after 115.7
- Build 115.8 enabled **full** backend Pytest and Chromium Playwright on staging, plus isolated PostgreSQL 16 Alembic security validation. The isolated PG security run passed.
- Initial full-suite result: 11 failed, 767 passed, 1 skipped (12 subtests passed). Defects included new-edit keyword limits accepting more than 30 keywords and Command Centre geography showing source publications outside the selected date interval.
- Build 115.9 fixed both genuine workflow defects and repaired stale tests (old authorization expectations, duplicate QA fixture IDs, old narrative assertions); second full-suite result: 1 failed, 777 passed, 1 skipped (12 subtests passed). The remaining narrative wording assertion had a punctuation mismatch.
- Build 116.0 passed the complete backend test stage (778 passed, 1 skipped), the PostgreSQL security workflow, and the React production build; Render reached Live.
- Initial 116.0 full-browser diagnostic selected 56 tests (3 historical cases explicitly excluded); Chromium stopped at 5 failures. Three failed due old Social Listening controls removed in V3 (Saved Searches / Review Queue / old Campaign modal / old assessment pilot accordion), one asserted the obsolete Home navigation, and one demanded an exact Access Denied heading instead of asserting API denial and absence of data. An optional pilot_smart_radar.topic_summaries table also caused a 500 in clean SQLite QA sessions. These findings require modern browser tests and a graceful optional-storage fallback.
- 116.1 fix candidate: optional topic cache storage must return an informative unavailable result without queuing AI if the legacy schema is absent; pilot sample only contains actual Captured Posts; align browser acceptance tests with V3 campaign-first UI and verify out-of-scope evidence denial via the authenticated API.
- Supabase RLS snapshot: **all 39 public tables have RLS enabled; zero allow policies**. The Data API is deny-all under its normal roles despite grants; the backend uses authenticated server-side authorization. This check is a policy snapshot, not proof against all possible privilege escalation.
- Source audit: no orphan assessments, orphan human reviews, duplicate campaign/result ID pairs, or malformed candidate/topic JSON. No officer decisions or source evidence deleted.
- Remaining manual model-quality requirements: review the **93** latest UNASSESSED relevance labels, **23** UNKNOWN/UNCLASSIFIED sentiment labels, topic gaps and historical duplicate URLs against a human gold baseline. Automated API and browser tests cannot certify 100% model classification quality.
