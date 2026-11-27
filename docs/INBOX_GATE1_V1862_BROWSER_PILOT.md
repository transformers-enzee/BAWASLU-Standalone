# BAWASLU v186.2 — Isolated UI-to-PostgreSQL Human Gate 1 write-pilot acceptance

Staging-only branch: `architecture-v2-foundation-20261015`.
Previous release: v186.1 live on Render staging.
Purpose: verify the REAL browser, authenticated FastAPI routes, and actual PostgreSQL writes without mutating BAWASLU Supabase or existing officer data.

## Test topology

GitHub Actions `.github/workflows/bawaslu-gate1-browser-pilot.yml` creates a brand-new throwaway PostgreSQL 16 service within its runner. A guarded script seeds:
- Fictional QA campaign `BAWASLU Gate 1 QA Pilot` in DRAFT, with one ordinary synthetic source `GATE1_QA_SYNTHETIC` and one watchlist-account-only source to verify exclusion.
- Fictional protected operational campaign with an ordinary non-QA source.
- Local CI-only administrator with nationwide view, edit, human-validation and administration permissions; separate read-only viewer.
- One saved offline assessment for each ordinary campaign. **No AI/SocialCrawl API calls or real source ingestion.**

The script refuses all databases except localhost/127.0.0.1:5432/bawaslu_gate1_pilot_ci, with the expected disposable username and two explicit CI opt-ins. Seeding stops if the database already has any user, campaign, source or assessment; no pre-existing records may be overwritten. The server runs with `BAWASLU_STARTUP_READ_ONLY=true` and only 127.0.0.1 network binds.

Both backend and frontend run as the real app on GitHub's ephemeral runner. Playwright tests authenticate through the actual login page and exercise the real `/inbox?gate1=1` officer UI (not mocked API calls).

## Acceptance coverage

1. Administrator sees a fully eligible **synthetic** pilot with zero ordinary non-QA links. Watchlist-account-only links are not counted as ordinary evidence.
2. Officer opens original fictional saved text and sees initial AI relevance `IRRELEVANT`.
3. Changing relevance to `RELEVANT` appends version 2; original version 1 remains `IRRELEVANT`. A stale old-tab HTTP correction must return 409.
4. Changing sentiment from saved AI `NEGATIVE` to officer `NEUTRAL` preserves both labels, and a second correction to `POSITIVE` is tracked separately.
5. `OFFICER_VERIFIED` only marks the saved information snapshot reviewed; a later sentiment correction triggers `REVALIDATION_REQUIRED`. The officer can filter by that status.
6. Restoring historical relevance `IRRELEVANT` adds version 3 rather than deleting versions. UI audit history shows the restoration.
7. Viewer can read evidence but not edit, a test without authorization returns 401, an unauthorized write returns 403, a watchlist-only source returns 404, and a simulated operational campaign cannot be used for QA writes.
8. A separate Python post-browser audit directly reads PostgreSQL to assert **exactly** three assessment versions, two sentiment corrections, five Gate 1 audit events, unchanged raw provider payload, no promoted intelligence/Command Centre publishing, and an untouched separate campaign.
9. Browser network checks assert no paid provider requests or JavaScript runtime errors. All source data and account identifiers are fictional.

## Runtime and deployment safety

This CI workflow may set `BAWASLU_INBOX_GATE1_WRITE_ENABLED=true` **only inside its disposable runner process**. It does not update Render environment variables and has no Supabase connection strings/keys.

On Render staging v186.2, preserve the existing disabled write configuration. The production environment and shared BAWASLU Supabase remain unchanged. Do not seed campaign ID 12, enable its write allowlist, or use it for live correction writes without an explicitly approved independently isolated database.

No billable database, Supabase branch, new Render service, model training or paid AI calls are created for this release.

## Changes

- Add isolated SQL fixture seeder and independent post-browser audit.
- Add real browser E2E test and mandatory GitHub Actions isolated PostgreSQL workflow.
- Tighten QA pilot readiness to compare only ordinary evidence links, excluding watchlist-only links.
- Add mandatory offline fail-closed seed security tests.
- Advance build version to v186.2.

## Remaining manual QA

Once v186.2 passes all CI checks and is deployed **read-only** to staging, a short officer-facing read-only smoke test suffices to confirm the pilot-readiness panel still reports QA DRAFT / 0 synthetic / NOT READY. Live write testing on Render is separately gated by an isolated application database and explicit administrator approval.
