# BAWASLU v153.6: Command Centre management follow-up

Single bulk build adds a read-only management queue for already-authorized cases CREATED in the selected UTC reporting period. It uses existing status, latest report version and the latest original-source review event OBSERVED inside that period. No hidden lifetime verification inference. One actionable suggestion maximum per case, grouped into P1/P2 review order (not legal severity) and capped to 12 displayed cases while retaining complete counts for the authorized cohort. Closed cases and those with approved reports and no outstanding identified workflow status are excluded from follow-up.

The existing Reports & Briefings screen shows case IDs, next checks, status, a priority filter and safe Inbox casework links that recheck permissions. Management report draft recommendations include the first three case-specific follow-ups, carried through existing PDF, DOCX and XLSX renderers, with explicit caveats and unsigned status. No source text, audit notes or new casework actions are returned. No additional DB queries, no Supabase migration, no paid provider calls or automatic legal determinations.

Mandatory backend and frontend regression tests cover scope, historical review uncertainty, report version precedence, safe URLs and export integration.
