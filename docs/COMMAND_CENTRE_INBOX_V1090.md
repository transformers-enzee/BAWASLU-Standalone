# v109.0 · Command Centre and Intelligence Inbox

Bulk changes made in staging branch:
- Command Centre header renamed from Smart Radar, V6.2 layout preserved
- Level-1 summaries grounded in saved source issue cues and officer-recorded concern descriptions; not new paid AI inference
- Priority Candidate Watchlist uses the top ten saved Inbox mentions, matches registered profiles and offers a permission-checked, user-confirmed Add action. No automatic candidate creation
- Conversation Activity includes source-date period, observed-days and busiest publication date
- Geographic Signals uses the Indonesia provincial SVG map already used by Social Listening and clearly distinguishes unverified location mentions from human-confirmed incident locations; unknown names are not assigned
- Sentiment and Platform distributions use linked donut charts that open matching original evidence
- Inbox has sentiment filtering and explicit per-post flag and sentiment badges at the right, plus post and flagged counts inside Statistics

The existing Inbox saved-classification feed remains the only operational post source.
Candidate Watchlist registry is used only for registration, priority and user-authorized Watchlist changes.

Full-dataset sentiment inference is NOT run by this UI release. It is a separate,
potentially billable action requiring a dedicated batch and QA.

Regression checks: backend tests on saved evidence and false legal claims,
frontend contract checks and the existing CI visual/build/smoke suites.
