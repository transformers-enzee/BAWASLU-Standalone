# v155.8: One next action per saved-source pilot row

Without changing any source evidence or casework permissions, the read-only pilot endpoint now derives a single operational next-action code from current eligibility, saved text/URL completeness, jurisdiction freshness, flag assessment drift, and existing visible case status. Priority: inaccessible source; latest assessment irrelevant; incomplete saved evidence; changed jurisdiction confirmation; changed flag assessment; existing active case; then normal Inbox officer review. Other source warnings remain visible. Counts are preview-only, not full-population or confirmed legal findings. Bilingual officer summaries appear next to each record and in a compact preview summary.

The existing authorized casework source link remains human initiated; no assignment, approval, legal decision, paid provider query or Supabase mutation occurs. Isolated SQLite and frontend contracts cover every priority branch. No migration required.
