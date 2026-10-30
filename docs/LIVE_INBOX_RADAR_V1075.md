# BAWASLU v107.5 — Live Smart Radar from Intelligence Inbox

## Operational source of truth

The Smart Radar dashboard, source details, trends and review action targets
derive from the SAME permission-scoped `campaignIntelligenceInbox` action that
supplies Intelligence Inbox. The previous `pilot_smart_radar.source_posts` and
`pilot_smart_radar.post_assessments` no longer power operational Radar views.
Historical pilot source references remain available only in archival tools.

- Relevant / highly relevant **latest saved** assessments enter Radar.
- Irrelevant and unassessed source posts remain in Social Listening and are
  excluded from both Inbox and Radar.
- One distinct original social source ID is counted only once across campaigns.
- Saved sentiment, topic tags, candidate annotations and human-review
  statuses are reused without charging AI credits.
- Potential Violation flags are source-specific, preliminary and derived
  from existing quote-validated saved indicators / officer review.
- Human-review flags suppressed in Inbox are not revived in Radar.
- Public concerns and topics group **discussion only**, never a shared
  physical incident. 'Recurring' requires two independent URLs and accounts.
- Officer Radar triage history is separate from Inbox's evidence review
  decisions; existing pilot-prefixed review-state tables store triage state
  only, not the evidence driving new operational findings.
- Regional officers see only Inbox-authorized campaign-linked sources.
- Original source URLs and canonical `social:<id>` references are retained.
- The existing Inbox request returns at most 300 findings; Radar explicitly
  signals when that cap may have truncated its coverage.

## Automated acceptance

Backend unit tests verify routing, data lineage, current relevance,
cross-campaign dedup, no keyword-to-violation promotion, human dismissals,
recurrence evidence, sentiment, source metadata, and preserved triage state.
The frozen Smart Radar V6.2 frontend remains unchanged visually; its live
bridge now REQUIRES `mode=SAVED_INBOX_SOURCE_OF_TRUTH` and rejects a legacy
pilot payload rather than silently showing it.

No AI processing, database schema migration, or SocialCrawl requests
are invoked by this change.
