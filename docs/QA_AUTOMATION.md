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
