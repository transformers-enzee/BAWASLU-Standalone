# Social Listening — SocialCrawl Foundation

BAWASLU v0.1 includes a Social Listening foundation using SocialCrawl as the initial provider. Social listening is an evidence-discovery workflow; provider results are not BAWASLU findings and do not become Intelligence until a human explicitly promotes them.

## Flow

`Saved/Search Filters -> SocialCrawl -> Raw Provider Evidence -> BAWASLU Deduplication -> Review Queue -> Human Decision -> Optional Intelligence Promotion`

## Filter contract

The BAWASLU filter model supports keyword, exact phrase, include/exclude terms, hashtags, accounts/handles, watchlist IDs, issue category, topics, locations, province, regency/city, date range, lookback days, language, platform, content type, minimum relevance, minimum engagement, minimum followers, verified-only, source include/exclude, comment enrichment, sort and result limit.

Provider-native filters are sent to SocialCrawl where supported. BAWASLU applies additional local filters after normalization when the provider does not expose an equivalent parameter. This keeps the UI contract stable as provider capabilities evolve.

## Initial platforms

TikTok, Instagram, YouTube, Facebook, X/Twitter, Threads, Reddit and LinkedIn. The platform list is a configuration capability, not a permanent hard-coded product limitation.

## Provenance

Each result retains provider, provider request ID, provider result ID, platform, canonical URL, observed account/handle, published/collection timestamps, language, provider relevance, engagement fields, source-identity resolution, content fingerprint and raw provider payload.

## Human governance

Review states: `DISCOVERED`, `RELEVANT`, `MONITOR`, `NOT_RELEVANT`, `PROMOTED`.

Promotion creates an ordinary BAWASLU Intelligence record with `UNVERIFIED` evidence status and `Pending Review`. It does not bypass jurisdiction confirmation, evidence verification, triage or final human review.

## SocialCrawl API assumptions

The adapter uses the documented Universal Search path `/v1/search/everywhere`, `GET`, `x-api-key`, JSON response envelopes, and an idempotency key. The base URL is configurable with `SOCIALCRAWL_BASE_URL` so deployment can follow the provider's current host without code changes.

The provider documentation describes unified response fields including `credits_used`, `credits_remaining`, `request_id`, `cached`, computed language, engagement rate and estimated reach where supported.

## Cost governance

Every provider call records endpoint, request ID, credits used, credits remaining, cache status, result count, user and timestamp in `social_listening_provider_usage`.
