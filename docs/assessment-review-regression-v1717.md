# v171.7 — Administrator review regression enforcement

- The consolidated advisory approval gate fails closed when the cross-snapshot audit is omitted.
- The UI warns on older APIs that lack the consolidated gate; legacy capacity must not be treated as authorization.
- GitHub Playwright QA explicitly runs the v171.4–v171.7 frontend contract scripts before the production frontend build.
- Two isolated Chromium scenarios check review-gate warnings and confirm only the read-only status endpoint is invoked.
- Three pure backend tests verify missing and contradictory snapshot evidence and prevent accidental paid processing.

No database migrations, paid AI requests, worker claims, record changes, or deploy settings are introduced.
