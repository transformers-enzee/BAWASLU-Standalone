# BAWASLU Release Readiness

## Current release status

Build 52.0 is the signed-off UAT baseline for the completed standalone BAWASLU workspace.

### Feature-complete modules
- Home
- Watchlist
- Social Listening
- Intelligence Inbox
- Intelligence Assistant
- Add Intelligence
- Data Sources
- Validation
- Administration

### Social Listening production verification
The production Google News / Online News path has been manually verified by the project owner:
- 1-credit preflight and confirmation;
- real Google News results returned and stored;
- human review state changed successfully;
- a reviewed item was promoted into Intelligence;
- the promoted Intelligence record opened successfully.

Automated CI continues to use fake/local providers only and must not spend SocialCrawl or OpenAI credits.

## Release gates

A release is ready for client/UAT handover when:
1. backend pytest passes;
2. production frontend build passes;
3. Playwright zero-credit QA passes;
4. Render deploys only after CI success;
5. no known P0/P1 workflow defects remain;
6. any paid-provider production check required by a provider-flow change is performed manually by the project owner.

## Deferred / future modules

The sidebar items marked as future modules remain intentionally deferred and are not part of the current release scope:
- Command Center
- Risk & Early Warning
- Action Center
- Intelligence & Reporting


## UAT handover checklist

Use this checklist for the client/UAT pass:
1. Sign in as a National Administrator and confirm all completed modules are visible.
2. Sign in as a regional analyst and confirm geography and permission restrictions.
3. Create or open a Watchlist item and confirm authorized visibility.
4. Run a zero-credit Social Listening saved-search management flow; paid provider searches remain manual.
5. Review a stored Social Listening result and confirm the selected review state is visibly highlighted.
6. Promote one eligible Social Listening result to Intelligence and open the created record.
7. Open the Intelligence Inbox and confirm scoped records/actions.
8. Ask the Intelligence Assistant a question and verify supporting-record traceability.
9. Add a manual Intelligence record and confirm it enters the expected review workflow.
10. Register/edit a Data Source as an authorized administrator.
11. Validate an eligible record and confirm jurisdiction/reviewer safeguards.
12. Change a user assignment in Administration and confirm audit history.
13. Toggle EN/ID and confirm app-owned labels change consistently.
14. Confirm no P0/P1 defect remains before handover sign-off.

## Known operational boundaries

- Automated CI never spends SocialCrawl or OpenAI credits.
- SocialCrawl production checks are manual and use Online News / Google News unless explicitly approved otherwise.
- Future sidebar modules remain intentionally deferred.


## Build 50.0 UAT defect hardening

The Intelligence Assistant now uses a canonical UTC representation for human-validation timestamps in both model grounding and supporting-record UI. The prompt requires exact reuse of the supplied UTC validation timestamp rather than model-side conversion.

Historical records that carry a validated status but do not satisfy current validation prerequisites are not silently rewritten. They are exposed as `LEGACY_GOVERNANCE_EXCEPTION` with explicit blockers so analysts can distinguish historical state from a clean current-rules validation.


## Build 51.0 UAT defect hardening

Intelligence record timelines now filter audit events by both `subject_type=IntelligenceItem` and the record's `subject_id`. This prevents audit events from unrelated object types that happen to share the same numeric ID from appearing on an Intelligence record.

A zero-credit backend regression test creates a colliding non-Intelligence audit event and verifies that it is excluded from the Intelligence detail timeline while the record's own creation event remains visible.


## Build 52.0 UAT closeout

Production UAT for the current release scope is complete. The manually exercised workflows include Social Listening promotion, Intelligence creation/detail, jurisdiction confirmation and validation, Administration geographic access changes and audit history, Data Sources persistence, dashboard/inbox visibility, and Intelligence Assistant grounding.

The UAT defects discovered during the pass were fixed in Builds 50.0 and 51.0 and subsequently re-verified in production. There are no known blocking defects from this UAT cycle.

The release is now in defect-fix-only mode. New feature development requires explicit scope approval.


## Build 53.0 Command Center development cycle

A new post-UAT feature cycle is opened with Command Center as the first upcoming module. The initial Command Center release is read-only and role-aware. It reuses existing authorized Intelligence and stored Social Listening queue data to provide:
- operational metrics with drill-down links;
- a ranked priority attention queue;
- Critical/High priority snapshot;
- geographic distribution within the user's authorized scope;
- links into Validation, Social Listening and Intelligence Inbox.

Opening Command Center does not call OpenAI or execute a paid SocialCrawl search.
