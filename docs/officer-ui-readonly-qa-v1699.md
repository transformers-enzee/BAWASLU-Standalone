# v169.9 — UI acceptance automation with production-safe separation

Adds a Playwright smoke suite for unauthenticated redirect behavior, admin login, core authorized officer routes, future-safe navigation links, Reports & Briefings entry point, JavaScript exceptions, absence of browser-side paid requests, and displayed build-version parity.

The GitHub Actions workflow starts its own local backend using **temporary SQLite** and its own local Vite server. The configuration refuses to run the smoke checks when PLAYWRIGHT_BASE_URL points to an external host. No staging or Supabase customer records are created or modified.

This automated smoke is not a substitute for real authenticated staging UI and human visual/accessibility acceptance. Browser CI needs a successful GitHub Actions run before the automated-browser component may be called passed.
