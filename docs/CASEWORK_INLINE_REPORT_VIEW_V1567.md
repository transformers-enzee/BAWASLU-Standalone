# v156.7 — Full report view accessible inside Inbox casework

Observed in staging UAT: clicking View report on Case #2, Reports #2 and #3 only populated the distant report editor below the report list. With a long modal list this looked like a no-op. The same action now expands a read-only preview immediately below the selected report card (and toggles closed when clicked again). It shows the title, saved status, four complete report fields, and any preserved return feedback without requiring the officer to scroll through the editor to understand what opened.

Existing editor prefill remains available for authorized draft revisions. Read-only preview is available for previously returned and approved historical reports without enabling editing or changing reviewer permissions. This release is UI-only: no database schema migration, reports mutation, paid inference or casework action. Frontend static contract and full Render frontend production build verify behavior.
