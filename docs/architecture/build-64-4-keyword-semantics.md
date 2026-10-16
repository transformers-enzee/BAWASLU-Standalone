# Build 64.4 — keyword semantics (pre-provider QA)

Main keywords are OR-matched locally and exclusions take precedence.
Secondary keywords are optional context annotations, **not** extra
requirements. These are literal case-insensitive substring matches,
not AI determinations. A match is never proof of a violation.

The collection simulator preserves the main/secondary match terms
with each CampaignEvidence link without rewriting the source record.

**Important provider caveat:** SocialCrawl currently receives multiple
main keywords combined in one query string. This has **not been proven**
to implement OR at provider retrieval time. Even correct local OR
screening cannot recover posts a provider search never returned.
Do not activate the live scheduler or claim full OR recall until
provider syntax is validated in a user-approved paid UAT. Preview
the maximum expected credits before the user executes that test.

No production migration, provider request, or paid crawl in this change.
