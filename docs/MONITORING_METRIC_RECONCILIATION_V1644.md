# v164.4 — Verify aggregate dashboards against their distinct-source inventory

Extends the existing v164.3 count-integrity responses with checks that the Command Centre's platform counts and publication-day totals equal its distinct captured source IDs in the selected period. Smart Radar checks that its platform and sentiment distributions agree with source-level values from the existing selected, relevant Inbox window, and that its reported source total matches the distinct source IDs. Repeated source IDs across topic groups are explicitly flagged rather than treated as independent conversations.

Both checks use in-memory data already assembled for the authorized dashboard. There are no new database reads, AI/provider calls, mutations, admin screens or migrations. A mismatch is visible as a stable issue code, not silently corrected or represented as an incident. Matching sums do not prove sentiment correctness, independent sources, legal wrongdoing or comparability between the recent Inbox subset and Command Centre's publication-period captured population.

Regression tests cover clean totals, duplicate contributions, inconsistent sentiment/platform/day aggregates, unclassified sentiment and empty authorized scopes.
