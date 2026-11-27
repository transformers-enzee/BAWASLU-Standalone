# BAWASLU v186.0 — Human Gate 1 bulk integrity rollout / administrator preflight

Supersedes the failed, unpublished v185.9 staging image build. The v185.9 commit remained source-only because its mandatory full-backend regression failed 2 fixture tests (3022 passed, 1 skipped). The failure was a prior test officer profile missing geographic_scope=Nationwide, now fixed without relaxing the production post-lock geographic scope check.

## Included
- All v185.9 features: source integrity digest, stale-approval rejection, field/restore assessment/source concurrency tokens, AI-vs-officer relevance distinction, information QA filters, current-loaded-count rollups, revalidation upon source change, and enhanced audit regression.
- Source-row lock with a second geographic scope check on every Gate 1 correction, restore and information decision. National fixture now explicitly states nationwide access; a regional outsider is tested to fail closed with 404.
- Administrator-only GET /api/inbox/human-review/campaign/{id}/pilot-readiness:
  returns read/write feature state, staging pilot mode, campaign allowlisting, permission and ownership checks, readiness Boolean, and read-only/no-publication declarations. This endpoint cannot enable writes, return source evidence or modify a database record.

## Staging rollout policy
1. Keep v185.8 live until v186.0 passes all workflows and is explicitly saved as the new Render staging Docker image.
2. Deploy v186.0 while BAWASLU_INBOX_GATE1_WRITE_ENABLED=false. No pilot permissions or allowlists should be broadened during deployment.
3. When a disposable staging-only campaign is approved for a pilot, an authorized administrator can check the readiness endpoint. A non-admin must receive 403.
4. Only with explicit administrative authorization, staging pilot flags and campaign allowlist, test the correction, sentiment, restore, review decision, stale decision and regional permission cases. Never use original production officer records for QA.
5. Verify the original provider/source payload is unchanged; review status stales automatically after post/assessment changes; no AI training or Command Centre publication occurs. Turn write flag off again after pilot.
6. Gate 2 approval and Gate 3 training remain separate projects and are NOT automatically triggered by a Gate 1 write or officer-reviewed state.

## QA and data boundaries
- CI full backend regression, source-lock geographic security, in-memory SQL database tests, frontend builds, browser QA and GHCR publication are mandatory.
- No schema migration, RLS change, direct Supabase Data API exposure or paid AI processing.
- Information QA coverage metrics are for loaded authorized samples only, not a population-level accuracy score or election violation statistic.

Build version: v186.0. Staging branch: architecture-v2-foundation-20261015.
