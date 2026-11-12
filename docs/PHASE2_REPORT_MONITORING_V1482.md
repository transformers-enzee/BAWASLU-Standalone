# BAWASLU Phase 2 — Optional Inbox Monitoring in Management Reports (v148.2)

**Staging only:** `architecture-v2-foundation-20261015`.  
**Purpose:** Give management separate source-grounded monitoring and officer-casework views without a second dashboard or a paid AI call.

## Current limitation

The prior management report correctly counted authorized officer cases and report versions but could not describe social monitoring where no case assignment had been created. It was inappropriate to interpret `0` case assignments as `0` monitored public discussions.

## Delivery

- The existing **Command Centre → Reports & Briefings** adds an opt-in **Include saved Inbox monitoring** switch. The default is **OFF** to keep routine casework reporting fast.
- When selected, server-side reporting uses the **same permission-scoped, relevant, saved Inbox findings** as Command Centre. One canonical social source is counted once across linked campaigns. The report does not fetch unrestricted social content or call any AI provider.
- Monitoring time filters are evaluated on the original post publication timestamp with an explicit timezone offset, not on officer assignment creation or crawl time. Missing, date-only and ambiguous timestamps remain separately reported as **unknown** rather than being put into an arbitrary day.
- The report displays separately: saved relevant sources published in the selected period, potentially flagged posts (only preliminary source flags), public concern posts, platform counts, and sentiment counts.
- The original casework KPIs remain unchanged. The management report preserves the different denominator, geography, publication-date and window restrictions of each panel.
- PDF, Word and Excel export endpoints accept `include_monitoring=true`, add monitoring numbers and methodology caveats to their same unsigned interim template, and return `X-Report-Monitoring: SAMPLED_INBOX`. CSV remains a **casework-only** export; it is not silently mixed.
- UI shows the monitoring switch and a separate panel; no fifth intelligence player, top-level navigation item, legal verdict or duplicate data registry is created.

## Mandatory caveats

- Inbox window: up to 300 links **per permitted campaign**, with unknown truncation status; not all crawling results, online conversations or distinct authors.
- `published_in_period` is an observed, deduplicated count of posts with valid timezone-aware source publication time **within** the requested rolling UTC interval. Unknown dates and outside-period posts are separate; zero does not imply the absence of relevant monitoring.
- A potential-violation flag does **not** establish an election-law violation.
- Published-source monitoring is **not** based on the same denominator as casework assignment counts. Never sum them as a total.
- The temporary report remains `DRAFT_NOT_APPROVED`; an officer must verify the source and sign off before external distribution.
- All requests use existing campaign and province authorizations. Do not bypass review status or expand geographic visibility.
- No new Supabase tables or writes; no paid AI model calls; staging only.

## Automated acceptance

1. Backend tests for canonical source deduplication, sentiments/platform reconciliation, timezone validity, date windows, topic filters and province-scoped view separation.
2. One OFF default: old casework metrics unchanged and no additional Inbox fetch.
3. One ON option: only saved permission-scoped Inbox sources read, monitoring metadata present and sampled provenance explicit.
4. PDF/DOCX/XLSX exports match optional monitoring counts and retain unsigned template labels and private `no-store` headers.
5. Frontend/browser regression checks for the switch, panel, sample warnings and the export URL.
6. Version contract, full backend test suite, frontend build, Playwright, PostgreSQL security and exact-commit Render live deployment are all required before marking the release complete.

## Distinct acceptance work still open

An authorized human officer must perform the source-linked casework workflow and independent report review. The live PDF corpus still contains no officer-reviewed legal PDFs; software tests do not establish legal-document authority. AI Assistant answer quality and formal legal-content acceptance remain separate gates from this read-only monitoring report.
