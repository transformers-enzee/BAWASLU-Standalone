# v154.4 BAWASLU real-evidence officer pilot intake

**Verified source baseline (13 November 2026, read-only Supabase):**
- 786 existing Social Listening result rows, 636 campaign-evidence links, 7 intelligence items
- 0 officer case assignments, case reports and case transition events
- No production database inserts, updates, deletions, migrations or paid AI calls

**Operational problem:** The officer-pilot worksheet and five-stage trace cannot be formally accepted when no real casework exists. Instead of creating fictitious assignments, use existing saved, relevant, permission-filtered social evidence to prepare human-initiated casework.

**Implementation:** Existing Command Centre Reports & Briefings now offers an opt-in 'Find sources for officer pilot' action only to authenticated officers with the existing add_intelligence permission. The backend calls the existing cached permission-filtered Inbox finding compiler on demand. A pure helper deduplicates original social post IDs across campaign sources, prefers saved source flags over concerns/narrative awareness, checks presence of original text and a syntactically valid HTTP(S) URL, and provides up to 12 safe numeric-ID Inbox links with source-level review reasons. Candidate counts apply only to the cached authorized Inbox window, never the whole dataset. Raw post text, original URLs, author identifiers, unverified claims and private audit details are not returned in the shortlist.

When a matching active case is already visible under the current officer's jurisdiction, the shortlist links to it rather than presenting a new case form. Hidden cases are never exposed. When original evidence is absent, the link leads to the saved Inbox source for inspection instead of case creation.

**Critical security boundary:** Clicking 'Review in Inbox casework' does NOT create a case. The existing separate /api/casework/preview and POST /api/casework/cases revalidate saved relevance, the initiating officer's permission and province/jurisdiction before any write. No new casework permissions or automated approvals are introduced. Potential-violation flags and saved concerns are triage hints, not verified legal findings.

**Performance:** No new fetch on default management page load; the officer explicitly requests the cached Inbox shortlist. Existing case lookup is scoped in SQL, capped to 250 candidate records, and filtered again with _visible. No SocialCrawl or OpenAI credits consumed.

**Verification:** Backend + frontend regressions check cross-campaign deduplication, valid numeric links, URL scheme and credential screening, absence of raw text, viewer denial, source preview vs assignment, actual officer-created case reuse and no DB writes on shortlist reads.
