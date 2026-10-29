# Forward integration: Smart Radar reads Intelligence Inbox

Decision October 29: new Smart Radar processing should read saved Intelligence Inbox results, not attempt to merge old pilot records with unrelated Social Listening posts.

New authenticated GET /api/source-lineage/inbox-radar-feed/{campaign_id} exposes a scoped, versioned, read-only feed of saved Inbox assessments for Radar and other modules. The historic Radar pilot dataset stays separate; no ID is silently crosswalked and no provider calls happen on the feed.

This is the first backend data integration step, not frontend Radar migration or complete #13. Existing Smart Radar views still need to consume the feed and support legitimate source provenance. #12 must produce source-fingerprinted production drafts; #14 measured accuracy still open. The ledger remains 12/15 engineering DONE.
