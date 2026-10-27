# BAWASLU five-module integration QA — 28 October 2026

## Automated QA (no paid provider calls)
On pushes to `architecture-v2-foundation-20261015`, `.github/workflows/approved-ui-parity.yml` is configured to run:

1. Extract and syntax-check approved Smart Radar V6.2 and Watchlist V2.2 embedded JavaScript.
2. Syntax-check the same-origin live-data adapters.
3. Check static UI/evidence contracts across Smart Radar, Watchlist, Social Listening, Inbox, and Assistant.
4. Compile backend Python and run `backend/tests/test_assistant_history.py` (permission denial, conversation bounds, user isolation, deletion).
5. Run `npm run build` from `frontend/`.

**Evidence rule:** A committed workflow does not mean a successful run. Inspect the Actions tab and require a green `Approved UI visual-parity build checks` run for the latest branch SHA before treating automated QA as passed. Connector status lookup did not expose a completed Actions check when this document was written.

## Read-only staging lineage audit
Run on the staging server with the correct `DATABASE_URL` environment only:

```sh
cd backend
python -m scripts.audit_source_lineage
```

This reports aggregate missing URL, platform, publication time, original content, account, and source-ID counts for Social Listening, Intelligence Inbox, Watchlist mapping and the Smart Radar pilot batch. It makes no writes and calls no paid providers.

**Not yet approved:** A single canonical ID spanning `social_listening_results.id`, `intelligence_items.source_id`, and `pilot_smart_radar.source_posts.pilot_post_id`. They are separate namespaces until an explicit mapping and migration are implemented and tested. Never equate them by name, substring, or raw number.

## Manual staging QA — required before final sign-off
Manual QA is necessary for actual browser rendering, live sessions and officer decisions. This is a small UAT pass, not a redesign request.

- **Smart Radar:** Open `/` and `/smart-radar`, verify original V6.2 three-level layout, all five operation players, two perspectives, Action Desk, source drilldowns and visible error handling. Do not claim AI-ranked priority when no assessment score is stored.
- **Watchlist:** Verify V2.2 cards, Add Candidate, full six profile tabs, sentiment empty states, original-source links, Stop Tracking confirmation, evidence retention and mobile layout. Check activated vs inactive candidates.
- **Social Listening → Inbox:** Review an existing collected campaign post (no paid search), inspect original URL, mark relevance, promote if authorised, follow its campaign/deep link into Inbox, compare source IDs/text/timestamps, and confirm officer review history survives refresh.
- **AI Assistant:** Ask once only with approved sample data, verify answer sources link to original posts, reload and reopen history, then log in as a different officer and confirm history isolation. Conversation history reads/deletes should not call OpenAI.
- **Access and responsive:** Repeat as read-only Viewer and an authorised officer; confirm mutation controls are disabled or rejected for Viewer. View widths 375px, 768px and desktop, verify navigation and drawers do not clip.

Use non-production test records for any save/delete/review action and check audit events after the test.

## Scope not touched in this batch
No schema rewrite of source identity tables, no change to QA Lab V17, no auto-triggered SocialCrawl searches or billable AI assessments, no deployment/Render settings modification, and no merge/PR.
