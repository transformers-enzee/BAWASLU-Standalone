# BAWASLU Phase 2 — Officer Follow-up and Audit Integrity (v147.7)

**Staging branch:** `architecture-v2-foundation-20261015`  
**Design:** Command Centre finding details → source-specific Intelligence Inbox casework; no new navigation module.  
**Delivery:** Single bulk code release, sequential build version, backend + frontend + security + browser QA.

## Verified staging data limitation (12 November 2026)

A read-only query to the connected Supabase database returned:
- 0 recorded case assignments
- 0 recorded case reports
- 0 recorded case transitions
- 0 officer-reviewed legal PDFs

The automated tests therefore use isolated SQLite fixture cases. **Passing those tests does not demonstrate real BAWASLU officer acceptance or approve any actual legal source.**

## Bulk changes

1. **Contextual handoff.** A Command Centre finding contains authorized saved Inbox social source IDs. The assessment endpoint offers up to eight links carrying the exact source and campaign IDs into the existing Inbox casework. The server query reuses an already visible, active case when one exists instead of suggesting another one. Viewers without assignment permission can open visible existing cases but are not offered a new-case link. No write occurs during assessment reads.
2. **Officer report version integrity.** `needs_my_review` and Assistant workspace report counters use only the latest case report, not every historical submitted version. Older submissions cannot be approved or returned after a newer report is created; stale draft edits also fail with HTTP 409. Prior versions remain readable audit history, with old-version action buttons hidden.
3. **SQL-first jurisdiction.** The current 300-row casework queue and assistant workload read apply province visibility predicates in SQL before limiting rows. The existing Python per-record visibility checks remain as a defense in depth. Queue counts still describe a **recent 300-case window**, not a complete all-time workload.
4. **Automated regression QA.** SQLite unit/integration tests cover source deep-link restoration, existing case reuse, province isolation, viewer read-only access, forged source IDs, latest-version-only approval, independent reviewer requirement, stale report rejection, and 320 unrelated out-of-province rows. Frontend build checks confirm the deep link, no automatic case creation, current-version buttons, SQL scoping, and matching build versions.

## Safety limits

- No automatic legal verdict, platform takedown, human approval or new assignment.
- Officers explicitly initiate the existing workflow and the backend rechecks permissions and saved source relevance.
- No production deployment, Supabase schema change, live case creation or paid model request in development or QA.
- The pending legal-content gate remains unchanged until authorized BAWASLU personnel review current laws and SOPs.

## Acceptance distinction

**Code release gate:** GitHub backend QA, frontend production build, UI/contract checks, version contract, PostgreSQL-security check, Playwright browser suite, and exact-commit Render `live` state.

**Operational acceptance gate:** A real authorized officer has to create/review a source-linked case, verify evidence, assign to the competent department, submit a report and obtain independent approval. This cannot be truthfully marked complete while the live casework tables are empty.
