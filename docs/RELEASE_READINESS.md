# BAWASLU Release Readiness

## Current release status

Build 48.0 is the release-readiness baseline for the completed standalone BAWASLU workspace.

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
