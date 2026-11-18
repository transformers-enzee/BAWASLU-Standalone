# BAWASLU v166.6 — Unified assessment operations view

This batch adds the authenticated, campaign-scoped read-only action `campaignAssessmentOperationsOverview` and an on-demand panel in Social Listening > selected Campaign > Campaign Overview. The panel displays pending and eligible job counts, unqueued evidence, reserved request limits, completion lineage, stale jobs and review categories. It intentionally does NOT load these heavier queries during normal dashboard rendering: the officer opens the details explicitly.

The backend composes existing access-controlled assessment coverage, AI worker readiness, completion audit and interrupted-job preview without creating a new path to paid processing, quarantine or database mutation. All write actions retain separate permission and explicit confirmation. No source text, individual IDs, keys, or officer case content is returned.

As last verified, campaign 2 had 29 pending jobs with zero attempts; campaign 4 had one stale PROCESSING job; and historical campaign 1 completion had ten usage-history discrepancies. The operational view reports current state, not assumed outcomes.

Automated QA covers campaign isolation, watchlist exclusions, missing jobs, deterministic review priorities, no side effects, frontend compilation and existing release regression checks.
