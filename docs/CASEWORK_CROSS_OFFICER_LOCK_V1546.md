# BAWASLU v154.6: Cross-officer duplicate protection & audited rerouting

## Problem
v154.5 prevented repeat submits from the *same* officer by locking that officer's User record, but two different officers could simultaneously create an active case for the same saved source and campaign. Additionally, when an officer submitted a different department, assignee or target scope for an existing active case, the API correctly reused the case without modifying it but did not explicitly tell the frontend the requested destination had not been applied.

## Changes
- Case creation still checks the officer's existing authorization, a **currently relevant saved assessment** for Social Listening evidence and any human-confirmed incident province before proceeding.
- The code then uses a **transaction-scoped PostgreSQL SELECT FOR UPDATE on the shared saved-source row**. For social evidence this is the unique CampaignEvidence(campaign_id,result_id) row; for formal intelligence it is the IntelligenceItem(intelligence_id) row. This serializes concurrent creation for the same saved source across officers and application workers until the case transaction commits. It avoids a schema migration, new unique index and new vendor credits. The saved row must still exist; a missing row fails closed.
- The server checks for an active case **visible to the requesting officer** with the identical source type, source ID and campaign. It returns the already-visible case rather than writing a new assignment or another audit event. A hidden existing case ID is never disclosed. Closed case history remains immutable and a newly authorized case may be created separately.
- The reused-case response now explicitly states whether the attempted receiving team, department and assignee match the existing case. **No routing changes occur on duplicate submission.** If the requested destination differs, the Inbox message instructs officers to use the existing separately audited Route action. This prevents misunderstandings about the fate of a case.
- The new v154.6 tests compile both source-lock queries with the PostgreSQL dialect to verify their FOR UPDATE clauses, and use isolated SQLite fixtures to exercise national-officer reuse, source disappearance, permissions, stale relevance, route mismatches, unchanged case data, no write-on-retry and closed-case retention. SQLite does not simulate PostgreSQL concurrency, so these tests do **not** constitute a measured live multi-connection race test.
- The v154.5 frontend contract is updated to recognize the stronger source-level locking and extended response fields, with an additional mandatory v154.6 frontend contract gate.

## Release safeguards
Staging branch: architecture-v2-foundation-20261015. Main database is Supabase. No live cases were inserted during coding or QA, no schema change, no paid AI/source crawl, no automatic legal or officer approvals. Formal human acceptance remains separately pending.
