# v165.6 — Supabase campaign-2 no-credit reconciliation

Live BAWASLU Supabase audit on 17 Nov 2026 identified precisely 29 campaign-2 KEYWORD links with latest UNASSESSED relevance and no assessment jobs. All had existing source rows. Distinct WATCHLIST_ACCOUNT rows are excluded. A conflict-safe SQL insertion created exactly 29 durable PENDING jobs with attempts=0 and explicit last_error='', created_at and updated_at values; follow-up read confirmed 29 PENDING jobs and zero missing KEYWORD queue entries. No OpenAI request was made by the reconciliation SQL and no evidence assessments were altered.

A raw SQL INSERT omitting last_error failed due to a PostgreSQL NOT NULL constraint; that attempt was atomic and inserted no rows. The subsequent corrected SQL completed successfully. The application enqueue helper now explicitly supplies last_error and timestamps when building its conflict-safe INSERT, instead of relying on application-side column defaults. A regression test asserts field population and repeat-call idempotence. The worker continues to choose pending jobs older than the latest 300 campaign links.

Important: PENDING is NOT the same as AI processed. Paid AI execution is not initiated by the batch. Existing budget reservations, job claim guards, and watchlist exclusions continue to apply.

The explicit backlog preview remains capped at the latest 300 links in a separate route; this is not a complete historical monitoring count.
