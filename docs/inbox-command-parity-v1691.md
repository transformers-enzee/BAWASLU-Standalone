# v169.1 — Inbox ↔ Command Center metric alignment

The Executive Command Center now applies the same pending-PRISM exclusion as Intelligence Inbox: an assessment with model_version=PRISM_PENDING_OPENAI does not count as an assessed or relevant source and cannot contribute executive alerts, issue inventories or summaries. The captured source remains visible in raw activity, with assessment coverage correctly counted as pending.

Activity platform labels are normalized using the same presentation vocabulary as saved Inbox-derived Command Center findings: twitter-ai-search, twitter and x display as X; instagram as Instagram. The raw provider values in Supabase remain unchanged.

Four isolated integration tests call the real campaignIntelligenceInbox and build_command_center using common synthetic evidence to verify relevant-source parity, exclusion of preliminary posts, correct raw-capture coverage, platform vocabulary and later IRRELEVANT revisions. All reads remain no-credit and scope-respecting. Differences due to user province permissions, timeframe or multi-campaign deduplication require separately scoped acceptance.
