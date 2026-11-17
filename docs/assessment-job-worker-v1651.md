# v165.1 — Durable queued assessment selection

The v165.0 reconciliation routine can enqueue the oldest eligible unassessed campaign links, but the existing background worker used the newest 300 CampaignEvidence links as its processing window. Once a campaign grows past 300 links, an old queued job could not be claimed.

The default worker now selects up to 200 oldest claimable PENDING jobs by joining durable AIAssessmentJob entries to ordinary CampaignEvidence links, respecting the campaign ID, WATCHLIST_ACCOUNT exclusion, and three-attempt cap. Explicit targeted analysis and the existing reanalysis path retain their prior scope. The worker still uses atomic claim transitions and reservation-based AI quotas; this release does not initiate an AI run or modify saved assessments.

Automated regression coverage verifies >300 historical links, excluded watchlist rows, state isolation, campaign isolation, bounded ordering, repeated read-only selection, and invalid batch limits.

Outstanding operational verification: whether campaign 2's 29 historical unassessed keyword links have been explicitly reconciled into PENDING jobs; safe AI execution remains separately gated. The separate campaign backlog preview still has a latest-300 scope and must not be used as a full historical coverage count.
