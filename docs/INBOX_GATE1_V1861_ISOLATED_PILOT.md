# BAWASLU SmartRadar v186.1 — Controlled Gate 1 write-pilot preparation

Date: 27 Nov 2026.
Branch: architecture-v2-foundation-20261015.
Target: Render staging only. Leave the live v186.0 service unchanged until v186.1 is fully verified and the user saves its image.

## Confirmed read-only observations from BAWASLU Supabase
- Created QA campaign: ID **12**, name exactly **BAWASLU Gate 1 QA Pilot**.
- Status: **DRAFT**. next_run_at: NULL. Campaign runs: 0. Linked evidence: 0. Assessments: 0. Gate 1 QA audit events: 0.
- The campaign creator has an Active National Administrator / Nationwide grant with view_intelligence, human_validation, edit_intelligence and administration permissions.
- The connected BAWASLU Supabase project has operational records; no separate development branch is present.
- No operational posts, permissions, sentiment corrections or campaign assessments were changed by the preflight queries.
- The staging environment's current write-flag values were NOT read back from Render; the endpoint supplies an authenticated read-only check after deployment.

## v186.1 safety constraints
Writing through Gate 1 is permitted ONLY if ALL conditions hold:
1. Read feature flag enabled.
2. BAWASLU_INBOX_GATE1_WRITE_ENABLED=true, and pilot mode exactly staging.
3. Explicit numeric campaign ID allowlist includes the QA campaign (no wildcard).
4. Campaign name exactly **BAWASLU Gate 1 QA Pilot**, status DRAFT (operational/active campaigns are ineligible).
5. Officer has view_intelligence, human_validation, edit_intelligence and standard campaign edit permission; geography is checked both on source lookup and again under source-row lock.
6. The individual source provider is **GATE1_QA_SYNTHETIC** with provider_result_id starting **GATE1-QA-**. Even linking a real provider source to the pilot campaign does NOT make it writable.
7. Current source digest, assessment ID and field revision match the submitted correction/review.
8. A valid reason is supplied, and all changes append audit entries while preserving originals.

The administrator-only pilot-readiness view is informational and cannot enable writes. It shows linked/QA/non-QA counts and whether all gates are satisfied. The UI only displays a button for the specially named QA campaign.

## Isolated automated write QA
The workflow `.github/workflows/bawaslu-gate1-postgres-pilot.yml` starts an ephemeral localhost PostgreSQL 16 service with a disposable empty CI database. Its tests:
- Create fictional synthetic source, saved AI assessment, campaign link, officer grant, and non-synthetic source for negative access tests.
- Check denied write with flag off; allowed synthetic correction when pilot-only flags set INSIDE THE TEST PROCESS.
- Check appending relevance/sentiment corrections, immutable original payload, history, stale revision rejection, OFFICER_VERIFIED and REVALIDATION_REQUIRED, restore-as-new-version.
- Verify an operational campaign and non-synthetic source remain unwritable even if accidentally linked.
- Verify two concurrent PostgreSQL corrections result in exactly one accepted correction and one stale revision conflict.
- Drops its ephemeral test tables; GitHub destroys its Postgres service after the job.

A fail-closed guard requires BAWASLU_TEST_DATABASE_URL hostname to be localhost/127.0.0.1, port 5432, database /bawaslu_gate1_pilot_ci, and BAWASLU_ALLOW_ISOLATED_DB_TEST=YES. These checks prevent accidental tests against Supabase or Render-hosted PostgreSQL. No paid AI/SocialCrawl requests are made.

## Remaining actual staging pilot decision
The BAWASLU Supabase project currently holds operational records. DO NOT seed synthetic QA posts into its shared public social_listening_results table, enable the write flag, or set campaign 12 in a live allowlist without a separate isolation plan and explicit approval. The completed isolated PostgreSQL tests are not a substitute for a later authorized end-to-end pilot on a dedicated database.

At this stage **real staging Gate 1 correction writes remain disabled**, and existing officer records have not been modified. Gate 2 insight publication and Gate 3 AI training are not invoked.
