# v160.6 — final regression coverage for the v160.4–v160.6 bulk batch

Include the v160.5 formal-source-versus-legal-source boundary test file in the Dockerfile's explicit backend release suite; otherwise these three new assertions would not run during the Render build. Maintain sequential backend/frontend build-version parity.

The release remains a lexical review-only safeguard, not an autonomous legal evaluation. Pending human tasks: independent model-answer scoring, legal-currentness verification, formal client sign-off, and authorized real-world UAT. The synthetic suite makes no live Supabase writes and consumes no AI credits.
