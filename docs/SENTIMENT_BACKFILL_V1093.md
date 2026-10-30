# v109.3 — Inbox simplification and authorized BAWASLU sentiment backfill

## UI
Remove the duplicate Five Intelligence Players / source finding summary block
from Intelligence Inbox; retain operational processing, historical QA and
acceptance diagnostics in a separately named section. The Five Intelligence
Players remain available in Command Centre.

## Sentiment run
User authorized AI sentiment classification of posts on 2026-10-30.
Scope is campaign id 1 and the campaign-source snapshot with result IDs <= 463.
At execution preview: 298 campaign-linked posts, 67 previously assessed,
190 requiring a provider call, 41 of the remaining had no prior relevance
assessment. The entire Social Listening source bank contains 463 records, but
unlinked records are not automatically assigned to this campaign.

This operation is intentionally disabled at code deployment. Enable explicitly
in Render with BOTH variables:
- BAWASLU_SENTIMENT_BACKFILL_ENABLED=true
- BAWASLU_SENTIMENT_BACKFILL_RUN_ID=BAWASLU-SENTIMENT-20261030

The worker reuses the existing paid, per-record campaignSentimentClassify
logic with a clearly attributed service actor. It skips any previously
assessed label (including model-confirmed UNCLASSIFIED), writes immutable
assessment versions and token-usage records, preserves relevance and
potential-violation annotations, applies a Postgres distributed advisory
lock, does not ingest new sources, and stops on a provider error instead
of silently retrying potentially billable requests.

The enabled run is bounded to <= 463 and a hard maximum of 350 paid
requests; subsequent/new source posts are excluded. No query/labeling of
unlinked sources is done as a side effect. The authorized run is initiated
only by the explicit Render environment-variable change.
