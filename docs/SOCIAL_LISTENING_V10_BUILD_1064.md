# BAWASLU Social Listening V10 — Build 106.4

Branch: `architecture-v2-foundation-20261015`
Scope: Saved-data presentation and campaign-specific Watchlist; **no paid API calls** and **no schema changes**.

- Correct the embedded Watchlist's campaign-specific "Mentions by Others" adapter: the campaign evidence API returns an array, whereas the unscoped actor API returns a records object.
- Preserve the existing candidate registry, account-owned evidence, authentication and selected campaign ID.
- Surface only previously saved unverified potential-violation flags from the Watchlist captured-feed assessments; no legal conclusions.
- Improve embedded Watchlist presentation to fit the Social Listening V10 campaign aesthetic; remove erroneous "sample" and "Example" labels.
- Add captured-post source-type and local text filters for the selected campaign, without extra crawling or AI charges.
- Keep `?tab=posts` and `?tab=watchlist` links scoped to the selected campaign.
- Expand integration checks for the scoped array contract and evidence filters.

QA: GitHub Actions approved-ui-parity (script syntax, integration contract, embedded UI smoke test, backend tests, frontend build); Render auto deployment should be confirmed separately.

Known limit: The campaignEvidence API provides up to 200 highest-ranked posts from up to 5,000 candidate records. A missing mention does not prove absence. Verified identity attribution and legal review remain officer responsibilities.
