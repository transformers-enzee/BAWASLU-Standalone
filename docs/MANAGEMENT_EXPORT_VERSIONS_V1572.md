# v157.2 Cross-format management report history

Word, Excel and PDF were built from a common interim template whose scorecard lacked the new v157.1 revision-history metrics. v157.2 adds stored and historical report versions, historical returned reports, latest approved after a return, and latest returned awaiting revision to the shared template and methodology. All three export renderers reuse those values.

The existing CSV casework export remains one row per authorized case but now appends latest report status, latest report ID, number of stored report versions, and historical-version count, computed from the same permission-scoped report window as the main briefing. It does not duplicate cases or count historical approvals as current approvals.

SQLite tests verify Word/Excel/PDF rendering, CSV latest-version counts, province restriction and returned-supersedes-approval behavior. No Supabase migration, AI calls, casework actions or extra user interaction. Export status remains an interim unsigned management draft, not legal clearance.
