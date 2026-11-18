# v170.6 — isolated authenticated-component QA

Add five Chromium tests using a locally served Vite component and mocked read-only operations API; never connect to Supabase, Render staging, or paid AI. Scenarios cover priority rendering, in-flight campaign switch and late responses, closing an in-flight snapshot, refresh errors with re-request, and aggregate drift warnings. Closing the panel now invalidates the outstanding request and clears stale data. Officer smoke suite build parity derives from local health rather than hardcoding v170.0. GitHub Actions executes both browser suites; frontend/server build version advances together.

These are isolated UI interaction checks, **not** real authenticated operator acceptance on staging.
