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
