# BAWASLU Standalone v0.1 — Release Notes

Date: 2026-10-07

## Objective

Move BAWASLU off a Base44-only runtime and onto the NK Intelligence standalone architecture without flattening BAWASLU-specific semantics.

## Implemented

### Social Listening / SocialCrawl

- New Social Listening primary navigation module.
- SocialCrawl Universal Search provider adapter foundation.
- Search filters for terms, exclusions, hashtags, accounts, geography, date/lookback, language, platforms, relevance, comments and limits.
- Saved monitoring/search rules and manual rule execution.
- Provider result persistence with raw payload and source provenance.
- Persistent deduplication via content fingerprint.
- Human review states and explicit promotion to BAWASLU Intelligence.
- Promotion preserves UNVERIFIED evidence and Pending Review status.
- Provider usage/credit logging (request ID, credits, cache status, result count, user).

## Core standalone platform

- Standalone FastAPI/SQLAlchemy service.
- PostgreSQL-ready database configuration with SQLite local fallback.
- Alembic baseline containing 21 application/migration tables.
- Existing BAWASLU React interface retained.
- Compatibility API preserves the `intelligence` and `registry` action shapes used by the existing UI.
- Server-side BAWASLU ACL by functional permission and geographic assignment.
- Source identity states retained: `REGISTERED_ACCOUNT_CONFIRMED`, `KNOWN_EXTERNAL_ACCOUNT`, `UNRESOLVED`.
- `observed_publisher_handle` remains separate from canonical registered identity.
- Human evidence verification remains independent from AI triage and final review.
- Jurisdiction confirmation and geographic mismatch review remain human-governed actions.
- Watchlists, public source accounts, actor relationships, categories, data sources, external connector definitions and audit are first-class tables.
- V3 triage-generation provenance is retained as a separate table with fingerprints/version fields.
- Base44 JSON migration staging retains raw records before commit.
- Migration mapping explicitly includes all 13 original Base44 entities.
- Original Base44 contracts are included unchanged under `legacy_base44_contracts/` as migration evidence.

## Verification completed

- Empty database upgraded successfully through Alembic.
- 21 standalone tables created, including four Social Listening tables.
- Backend automated tests: 9 passed.
- Tested: auth, intelligence creation/listing, observed source identity, registered source-account identity match, server-side province ACL, independent human evidence verification, migration coverage, SocialCrawl normalization/persistence, saved monitoring rules, human-controlled promotion, provider usage logging, and persistent social-result deduplication.
- Python source compiled successfully.
- No runtime frontend imports of `@base44/sdk` remain.

## Not yet production parity

- External AI provider integration is not yet connected; v0.1 triage is deterministic placeholder output and always requires human review.
- GovIntel-style hardened public-content retrieval has not yet been ported.
- Google OAuth and delivered OTP/password-reset workflows are not yet implemented.
- Evidence upload uses local filesystem storage, not production object storage/signed URLs.
- Frontend dependency installation/build could not be completed in the audit execution environment because npm package installation did not complete within the available execution window. The standalone frontend source/config was syntax-checked where possible, but a full Vite build remains a deployment gate.
- Full field-for-field migrated production dataset reconciliation requires an actual Base44 export dataset; only the importer contract and synthetic migration tests are included here.

## Recommended next version

`BAWASLU-Standalone-v0.2`: close production integration gaps, add scheduled monitoring execution, provider administration UI, hardened retrieval, and production AI/provider connectivity.
