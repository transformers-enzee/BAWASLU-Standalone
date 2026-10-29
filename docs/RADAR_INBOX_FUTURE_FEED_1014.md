# v101.4 Smart Radar Inbox-based source integration

Smart Radar's approved pilot remains intact. If `/smart-radar?campaign_id=<authorized id>` is opened, the page fetches the permission-scoped `/api/source-lineage/inbox-radar-feed/<id>` and displays source version links above the existing pilot frame. Data is sourced from saved Intelligence Inbox assessments; there is no automated pilot-to-social ID join, model call, or officer decision. For an absent campaign ID the historical pilot view remains unchanged.

This creates a genuine frontend consumer of the feed and a migration path. **It does not yet replace the entire historic Smart Radar pilot aggregation**, and #13 remains OPEN pending full module integration tests.

Wednesday staging: Render workspace has BAWASLU-Standalone architecture branch and bawaslu-intelligence main branch, neither verified isolated staging. Do not call staging DONE without isolation and rollback tests. Officer role comprehensive QA deferred as instructed.
