# BAWASLU v151.1 — Officer evidence review readiness and formal-source traceability

## Problems resolved
1. v151.0 could create an officer action to find a legal PDF for a legal question with no cited PDF, but its audit returned human_review_required=false when there were zero selected records and no direct enforcement wording. The UI and metadata were inconsistent.
2. Formal Intelligence records had valid citations but no dedicated review instruction to inspect the underlying evidence trail.
3. The normal officer interface displayed general source warnings but did not distinguish a missing legal PDF citation from ordinary uncited saved evidence.

## Implemented changes
- Human review is now required whenever there are concrete advisory officer review steps, even if no selected records were retrieved.
- Citation-coverage metadata differentiates LEGAL_REFERENCE_NOT_CITED, LEGAL_REFERENCE_CITED_UNVERIFIED, SELECTED_EVIDENCE_NOT_CITED, CITED_EVIDENCE_UNVERIFIED and NO_CITED_EVIDENCE. All categories explicitly mean presence/absence of source references, not factual truth.
- New TRACE_FORMAL_EVIDENCE_CHAIN advisory step directs officers to inspect a cited formal case record, its original evidence and review history. It carries only the currently displayed authorized INT IDs.
- Normal officers see short bilingual notices when no legal PDF page is cited for a legal question, or when saved selected evidence was not cited.
- Preserve the v151.0 read-only checklist, never automatically complete it or approve any case, legal claim or enforcement step.

## QA
Six new backend regression tests for no-evidence legal questions, social evidence mistaken for legal authority, formal records, mixed source order, uncited selected evidence and neutral no-evidence cases; frontend static contract checks for new notices. No paid AI calls, crawling, Supabase updates, schema migrations or production release.
