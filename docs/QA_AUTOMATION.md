# BAWASLU QA Automation

## Purpose

Playwright is used for repeatable QA that can run without consuming paid external-provider credits.

Automated coverage includes:
- authentication and logout;
- role-based navigation;
- protected-route checks;
- administrator self-protection;
- provincial geographic access controls;
- out-of-scope intelligence denial;
- Data Sources create/edit/persistence;
- Human Validation jurisdiction guards;
- mandatory reviewer notes;
- EN/ID navigation checks.

## Paid / metered provider policy

Automated CI must not consume paid provider credits by default.

The Playwright suite therefore does **not** execute:
- OpenAI AI Triage generation;
- OpenAI Intelligence Assistant synthesis;
- SocialCrawl paid searches;
- other future metered external-provider actions.

These flows remain manual QA unless a dedicated sandbox/free test provider or explicit test-credit budget is configured.

When a release changes a paid-provider flow, the developer should ask the project owner to run the relevant manual QA step and confirm the result.

For Social Listening production-provider QA, use **Google News / Online News only** unless the project owner explicitly approves another provider. The current application estimate is approximately **1 SocialCrawl credit** for a Google News-only search. Automated QA must never spend that credit. The developer should provide the exact manual steps and expected result, and the project owner performs the paid search.

## Local run

From `frontend/`:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

The Playwright configuration starts an isolated local FastAPI backend using `backend/playwright.db` and the local Vite frontend. It does not use the production database.

## CI

GitHub Actions runs the Playwright suite on pushes and pull requests to `main`. Failure artifacts include the HTML report and, when available, traces/screenshots/video.


## Social Listening hardening guarantees

The zero-credit automated suite also verifies production-safety rules around Social Listening:
- explicit empty or unsupported source selections are rejected before provider execution;
- ambiguous date-range/lookback combinations are rejected;
- regional review queues cannot inherit results from unscoped nationwide searches;
- non-national users only see their own provider-usage and repeat-search history;
- only the National Administrator receives cross-user Saved Search management override;
- promoted results are locked against later review-state changes;
- repeat paid searches require an additional acknowledgement in the UI.

These safeguards are tested with fake/local providers only and do not consume SocialCrawl credits.


## Google News response regression

Build 46.1 adds zero-credit regression coverage for Online News response normalization, including Google News payloads where articles are returned under `data.articles`. The suite verifies title/snippet/source/domain/URL/publication mapping, forced `online_news` platform tagging, and zero-result diagnostics that distinguish provider-zero, locally filtered, duplicate, and unusable rows.


## Google News wrapped-row compatibility

Build 46.2 expands zero-credit Google News regression coverage to support provider rows wrapped under an `article` object and source/publisher objects, while exposing field-name-only structural diagnostics when a provider row still cannot be mapped. Diagnostics do not expose article content.


## System-wide final regression batch

Build 47.0 adds a zero-credit authenticated smoke pass across the completed BAWASLU workspace routes and strengthens Social Listening review-state affordances. Review decisions now mirror the stored state directly in the action row using an active button style, check mark, and `aria-pressed` state in both Search Results and Review Queue. Promoted results remain locked.


## Release-readiness CI

Build 48.0 adds a production frontend build to CI before browser QA. This catches compile/bundle failures before Render deployment, while keeping all paid-provider keys empty.

The three legacy Playwright selectors still excluded in the workflow are not coverage gaps. Each has a maintained equivalent in `quarantined-fixed.spec.js`:
- provincial analyst navigation / protected routes;
- Data Sources geographic create flow;
- unresolved-jurisdiction validation guard.

These equivalents run in normal CI.
