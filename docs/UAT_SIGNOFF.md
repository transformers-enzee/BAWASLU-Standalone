# BAWASLU UAT Sign-off

## Release candidate
Build 52.0

## Sign-off status
- UAT owner: Project owner / BAWASLU Administrator
- Environment: Production Render deployment
- Result: PASS WITH NOTES
- Release state: UAT complete for the current release scope; defect-fix only unless new scope is explicitly approved.

## Acceptance summary

### Access and governance
- [x] National Administrator sees all completed modules.
- [x] Regional user assignment and geographic scoping behave correctly.
- [x] Administrator self-protection prevents changing the current user's own assignment.
- [x] User assignment changes are recorded in the audit/activity history.

### Intelligence workflows
- [x] Home dashboard loads and reflects authorized-scope operational metrics.
- [x] Watchlist loads and exposes expected management actions.
- [x] Intelligence Inbox loads with scoped counts, filters and review states.
- [x] Add Intelligence creates a reviewable manual record.
- [x] Intelligence detail preserves original source text and confirmed jurisdiction.
- [x] Intelligence detail audit timeline is isolated to the Intelligence record.
- [x] Validation blocks final validation until required jurisdiction/governance prerequisites are satisfied.
- [x] Confirmed jurisdiction permits final human validation.
- [x] Intelligence Assistant returns traceable supporting records.

### Social Listening
- [x] Google News / Online News production search returns usable results.
- [x] Review decision is visibly indicated on the selected result.
- [x] Relevant / Monitor review state enables promotion.
- [x] Promotion creates an Intelligence record and Open Intelligence works.
- [x] Promoted results are visibly locked.
- [x] Saved Search ownership/lifecycle and Not Relevant note requirements are covered by zero-credit automated regression tests.

### Data Sources
- [x] Authorized user can edit a custom source.
- [x] Source status/geographic scope persists after refresh.
- [x] Provider inventory remains visible with SocialCrawl available and NEWS API disabled.

### Language and UX
- [x] EN/ID application toggle is covered by system-wide Playwright regression.
- [x] No blocking client errors or broken completed-module routes were found in UAT.
- [x] Social Listening selected review state remains visibly highlighted.
- [x] Assistant supporting-record timestamps use canonical UTC and match the grounded narrative.

## UAT defects found and resolved

| Severity | Module | Description | Resolution | Status |
| --- | --- | --- | --- | --- |
| Medium | Intelligence Assistant | Narrative and supporting-record validation timestamps used inconsistent timezone presentation. | Build 50.0 canonicalized validation timestamps to UTC in grounding and supporting-record UI. | Closed |
| Medium | Intelligence Assistant | Historical validated record with unresolved jurisdiction could look like a clean current-rules validation. | Build 50.0 introduced explicit LEGACY_GOVERNANCE_EXCEPTION handling and supporting-record warning. | Closed |
| Medium | Intelligence Detail | Audit event from Social Listening appeared on an Intelligence record with the same numeric subject ID. | Build 51.0 filters timeline events by both subject_type=IntelligenceItem and subject_id. | Closed |

## Production UAT evidence summary
The project owner manually verified:
- Social Listening review -> Relevant -> Add to Intelligence -> Open Intelligence;
- human jurisdiction confirmation -> final relevant validation;
- National Administrator and provincial access behavior;
- Administration access-change audit activity;
- Data Sources edit/persistence;
- manual Add Intelligence creation;
- Intelligence detail audit isolation after Build 51.0;
- grounded Intelligence Assistant answer, supporting records, UTC timestamps and legacy validation warning.

## Known non-blocking boundaries
- Source verification remains separate from relevance validation; UNVERIFIED records are intentionally not presented as source-verified.
- Automated CI does not spend SocialCrawl or OpenAI credits.
- Paid SocialCrawl production checks are manual and use Online News / Google News unless explicitly approved otherwise.
- Future sidebar modules remain intentionally outside this release scope.
- Historical data may contain legacy governance states; these are surfaced explicitly rather than silently rewritten.

## Final decision
- [x] Approved for current release handover / operational use within the tested scope
- [ ] Approved with unresolved blocking defects
- [ ] Not approved

Any new issue after this sign-off should be treated as a UAT/production defect and grouped into a defect-fix batch. New feature work requires explicit scope approval.
