# BAWASLU v154.2: Officer acceptance evidence packet

**Purpose:** Prepare meaningful human-led officer acceptance without pretending that automated QA or an approved workflow status constitutes client sign-off. As verified on 13 November 2026, the connected casework tables had no actual case, report or audit records. Never seed the live database just to show a successful pilot.

**Modules:** Command Centre -> Reports & Briefings, existing authorized Inbox casework. No new standalone module or legal box.

**Implementation:** `officer_pilot_case_rows` uses the EXISTING five-stage `_acceptance_trace` and already jurisdiction-scoped reporting period. It returns one evidence-minimized case row per permitted assignment (case ID, operational status, current report status, five observed stage booleans, first missing audit check, conservative audit warning and permission-rechecked Inbox link). It exposes no post text, source URL, case title, review notes or officer identities. Dashboard preview is capped to 12; counts cover the entire permitted cohort.

**Read-only export:** `GET /api/management-reporting/officer-pilot.csv?period=weekly&topic=` requires the same authenticated profile and SQL visibility restrictions. Export contains ALL cases in the permitted reporting cohort, not only the preview, with original audit-stage observations and empty human officer assessment, independent reviewer, acceptance decision, date and notes columns. CSV uses field quoting and spreadsheet formula protection, contains no source material, and sends private/no-store and awaiting-human-review headers. When no cases match, it returns headers only, NOT fabricated cases.

**Human acceptance steps:**
1. An authorized officer selects genuinely collected casework and confirms the real original source.
2. The receiving officer checks the audit, ownership, jurisdiction and current report version.
3. The officer documents original-source access (unavailable and recheck are not success).
4. An independent authorized reviewer examines the submitted latest report; self-approval remains forbidden.
5. The responsible BAWASLU authority records the acceptance decision separately. Leave all worksheet human fields blank until actually assessed.

**Limitations:** Audit stages are observed only inside the selected UTC reporting window; previous history can exist. A full five-stage observation is neither factual authenticity nor formal client acceptance. Never use this worksheet to automatically approve, assign or take down content. No new DB schema, migration, AI call, or casework write. Automated SQLite regression tests cover permission and regional visibility, source corrections, current-version report state, CSV injection, non-exposure, empty worklists and export integrity.
