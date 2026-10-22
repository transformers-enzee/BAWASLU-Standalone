# BAWASLU Build 64.3 — Campaign collection preparation

Architecture v2 branch only. Production remains at Build 63.1 until the
Supabase backup/restore rehearsal, migration validation, and RLS issues are resolved.

## Implemented

- Read-only `campaignSchedulePreview` and `campaignHistory` in the Social
  Listening API, with regional visibility enforced.
- Per-run native SocialCrawl credit estimates and 24-hour shared spend
  accounting (including manual search usage).
- Fail-closed runtime gate: `automatic_paid_crawling_enabled=false`;
  there is NO live scheduled task and NO API enabling ACTIVE campaigns.
- Internal `simulate_campaign_cycle` method accepts only an explicitly injected
  test provider and a positive test budget. It cannot call the real network
  provider and is not exposed as an API endpoint.
- Simulated execution writes versioned Social Listening runs, links existing
  deduplicated evidence across campaigns, and backs off after provider failure
  by 15, 30 then 60 minutes.
- Campaign UI exposes Last Crawled, Next Crawl, estimated credits and
  existing collection history. Its language explicitly states that crawling
  is disabled.

## Not yet implemented / release gates

1. Approve a *separate* production scheduler design, global and per-campaign
   budgets, explicit billing permission, distributed lease/locking and alerts.
2. Validate provider syntax for multi-keyword OR queries and commentary
   collection; do not assume hashtag or comment availability.
3. Ensure deduplication is concurrency-safe across live provider workers with
   database uniqueness or serialization before any scheduled production jobs.
4. Restore production Supabase to isolated staging and dry-run Alembic upgrade;
   confirm row counts, permissions, RLS and rollback.
5. Finish Intelligence Inbox semantic relevance with retained raw evidence and
   human approval. A keyword match never proves a potential election violation.

The mock-only tests are not proof of production scheduling readiness.
