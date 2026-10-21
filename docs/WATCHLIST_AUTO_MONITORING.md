# BAWASLU Watchlist Automatic Monitoring (Build 87.9)

The Watchlist account-post feed supports a first-page SocialCrawl fetch as soon
as a public account is saved, followed by periodic checks while the web instance
remains running. New posts are deduplicated and linked to their Watchlist account.

## Opt-in deployment settings

No paid requests run by default. An administrator must set all of:

- `SOCIALCRAWL_API_KEY` to a valid provider key.
- `BAWASLU_WATCHLIST_AUTO_FETCH_ENABLED=true` (default false).
- `BAWASLU_WATCHLIST_DAILY_CREDIT_BUDGET=<positive integer>` (default 0).
- `BAWASLU_WATCHLIST_SYNC_INTERVAL_MINUTES=60` (default 60; min 15).

Each check uses `POST /v1/prism/profiles` with `include=posts` for one
public account, budgeting up to 2 SocialCrawl credits. LinkedIn/Web are not
supported in this budget-capped collector. Results are stored in existing
Social Listening evidence, plus additive Watchlist association tables.

The budget check considers all SocialCrawl credits recorded in BAWASLU during
the prior 24 hours, plus reserved ongoing Watchlist requests. If there are
insufficient credits within the configured cap, checks pause and retry later.
External usage outside BAWASLU must additionally be limited by the API key's
own spending cap at SocialCrawl.

## Scheduling and real-time limitations

Automatic collection is best-effort. The worker starts with the web app and
checks for due accounts every minute while the app is awake. A sleeping/free
Render web service cannot guarantee an hourly schedule. For production use,
run a continuously awake worker or connect an authenticated external scheduler.
Neither has been provisioned by this code change.

Each request retrieves the first page of the account feed. More historical pages
may exist. This is not a complete archive backfill and cannot guarantee every
new upload if many posts are published between checks. SocialCrawl does not
guarantee immediate publication webhooks for the basic profile-feed endpoint.

A successful check updates `watchlist_account_sync`, inserts/reuses evidence,
and records billed credits in `social_listening_provider_usage`. The dedicated
Watchlist Posts page refreshes stored evidence every 30 seconds while open; it
does not itself call SocialCrawl.

## Operational verification

1. Deploy the new code with the feature disabled and verify Build 87.9 loads.
2. Confirm the additive `watchlist_account_sync` and
   `watchlist_account_evidence` tables exist (startup metadata create_all).
3. Set an approved daily credit budget and API key; enable the feature only after
   approval. Use a separate budget-limited provider key where possible.
4. Register a test account and check the Watchlist Posts monitoring status.
5. Verify one provider usage entry, one completed Social Listening run,
   and deduplicated captured posts, then inspect subsequent scheduled checks.
6. Confirm that turning the feature flag off stops further paid checks after
   any in-flight request finishes.

This document does not authorize spending or claim a verified live deployment.
