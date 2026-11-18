# v168.5 cross-module UAT evidence

The administrator-only GET /api/integration/module-acceptance endpoint returns an aggregate cross-module inventory and explicit acceptance boundaries for Social Listening, Candidate Watchlist, Intelligence Inbox, Command Center, AI Assistant, Officer Casework, Management Reporting and AI Assessment & Classification.

One SQL aggregate statement queries only counts and a latest-version relevance coverage gap. No source content, URLs, personnel records or secrets are returned. A populated module is *not* certified production-ready, and the API does not infer completion percentages or client signoff. Inbox intelligence item counts are distinguished from social evidence. Candidate registry totals are not the two-slot campaign watchlist cap.

Real FastAPI HTTP authorization tests enforce national-administrator-only access. Isolated SQLite fixtures verify latest assessment version, scope separation, empty populations, no writes and no provider calls.
