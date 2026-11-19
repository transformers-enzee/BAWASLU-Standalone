# v171.8 — Restore release QA after historical monitoring fixture date expiry

v171.7 failed backend QA on the older v148.2 management-monitoring test:
the source fixtures carried a November 11 timestamp while the test moved
its reporting window using current UTC time. This correctly yielded 0
in-window published posts rather than the test's expected 2.

The fix uses a deterministic 12-hour offset from the test's runtime clock
for the two Riau posts and Bali sample. It preserves the original metrics,
scope, and access isolation assertions while avoiding historical-date drift.

This is a test-fixture repair only; monitoring aggregation and production
reporting logic are untouched. The frontend v171.4–v171.7 contracts still run
as a dedicated CI step. No DB writes or paid AI calls are introduced.
