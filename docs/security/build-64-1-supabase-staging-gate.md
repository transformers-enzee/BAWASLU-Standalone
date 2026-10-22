# Build 64.1 — Supabase hardening staging gate

**Task:** Supabase access-control verification before Architecture v2 production rollout.

The live BAWASLU backend uses SQLAlchemy/PostgreSQL. Supabase is the live
database. The application handles authentication and permissions in its API.
Direct Supabase Data API access by the `anon` or `authenticated` roles to
backend-owned tables is not part of this application's approved workflow.

## Verified initial observations

- Supabase project: `bawaslu-intelligence` (project ref `drunsmeiojllbazeokdm`).
- 21 legacy application tables were present, with 20 lacking RLS.
- The direct API roles had broad table privileges, including on
  `users`, `session_tokens`, and `intelligence_items`.
- The Architecture v2 branch adds six tables for campaigns, evidence
  relationships, assessments, human reviews, and issue phrases.

## Controls implemented in this commit

- `backend/security/64_1_supabase_security_ci_only.sql` is **strictly guarded**
  to a database named `bawaslu_security_ci` and an explicit ephemeral
  session flag. It must never be used as a production migration.
- The separate CI job creates a fresh PostgreSQL database, applies the
  complete Alembic schema, simulates the current excessive `anon`/
  `authenticated` table privileges, and verifies revocation and RLS
  while the backend database role still reads and writes.
- No project secrets, credentials, external network access, paid SocialCrawl
  requests, production database changes, or production deploys are involved.

## Remaining release gates (not complete)

1. Verify and document a usable point-in-time backup or tested restore.
2. Check the real Render backend connection role and separate any frontend
   components depending on the Supabase Data API (if any).
3. Test an approved security rollout on a **restored copy** of production data,
   not merely the empty-schema CI fixture.
4. Apply the security grant/RLS remediation with a reviewed and logged,
   separately approved production change. Supabase API grants and default
   privileges must be reviewed as part of that rollout.
5. Verify current records, accounts, endpoints, workflows, and read/write
   permissions; re-run security advisors.
6. Confirm monitoring and reversal plan. Disallow production release when
   critical checks fail.

**Do not merge draft PR #1 until the production database migration, backup,
privilege remediation, and staged integration tests are signed off.**

Note: this repo uses Alembic migrations executed on Render startup. Merging
the Architecture v2 branch triggers schema changes. It must remain draft until
the release gates above have passed.
