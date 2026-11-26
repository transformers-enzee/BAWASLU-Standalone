# BAWASLU v185.1 — Gate 1 information-quality QA within Governance Review

## Release reconciliation
- GitHub staging was already advanced by a separate chat to v185.0 (commit cb2c8bf11416); its 11 GitHub checks including Docker publication passed.
- Render remained on v184.9 at time of reconciliation. This v185.1 batch builds on v185.0, not v184.9, and **does not deploy** automatically.
- Supabase contains the two governance tables with RLS enabled and zero stored governance correction/insight trial cases. No schema changes made in v185.1.

## New read-only capability
- Administrator-only, campaign/jurisdiction-scoped Gate 1 quality sample available in the same v185.0 Human Review Status page.
- A bounded sample (max 120 recent ordinary campaign links; displays up to 20) includes **unassessed, uncertain, irrelevant and relevant** posts. It does not filter to violations.
- Officer sentiment precedence is shown without overwriting stored AI sentiment.
- Reports reviewer decisions and source-level deep links into the existing Intelligence Inbox for verification.
- Uses the latest saved assessment per source, excludes WATCHLIST_ACCOUNT-only links, avoids raw provider payload, and respects source/office scope.
- Counts are clearly labeled as recent-link **sample** statistics, not exhaustive totals.
- No paid AI calls, database writes, automatic retraining, or production activation.

## Manual QA gate
- Controlled read-only flag activation on Render staging and authenticated role/geography acceptance remain required.
- Governance write flag and pilot mode must remain OFF for initial manual read-only QA.
- Only request officer manual QA after live readiness checks and navigation have been verified on staging.
