# BAWASLU v179.7 — AI-5 scope recovery and document parity

## Evidence boundary from attached pilot export
The available attachment is a text transcription of two AI-5 answers, **not** the expanded Research Trail or a PDF. It includes no actual search queries, retrieved URLs, source excerpts, model input payload, or PDF structure. Therefore the exact historical call sequence cannot be reconstructed from this attachment; the code path and visible failures can be audited and re-tested. Do not claim a recovered historical query list from the transcription.

## Research path and failure location
At v179.6 the planner is capped at four dimensions, which may compress multi-part questions (election commission design, independence, comparative performance, neighbors, lessons, legal framework; or violation type/province/candidate/party/response/law). The candidate reader permits 12 initial + 6 follow-up pages, then a coverage check, but final synthesis was accepted even if it silently skipped requested parts. The old ReportLab PDF exporter flattened all heading levels into one style, replaced citations with opaque IDs and omitted inline clickable source names.

## Bulk changes
- Expanded scope planning to up to six independent dimensions and 14 initial + 6 gap pages. Planner and coverage auditor explicitly separate historical institutional descriptions from present-day measured outcomes.
- Added a bounded, independent post-generation answer completeness audit. For omitted user requests, it runs targeted public follow-up research (public modes only), then reconstructs the entire answer from allowed sources. One retry only. Remaining omissions appear explicitly in open questions and research warnings; never fabricate missing data. This is generic across topics. No external lookup of private saved context.
- General Research prompt leads with what is learned, explains study periods, differentiates formal institutional design from current performance and lets prose/table choices follow the question. BAWASLU Action remains a separate officer-workflow control, but research can answer requested practical or legal implications without switching mode.
- PDF exports preserve H1–H4 style hierarchy, paragraph and list layout, structured comparison where legible, readable inline clickable citations, original title plus publication date where available, a clickable source appendix and a compact Research Trail appendix. Export metadata remains permission-scoped.
- Chat source names also show publication dates where available, with research coverage and answer-audit findings available in the Research Trail.
- No Supabase schema or existing officer record is modified.

## Regression acceptance
1. Exact supplied pilot question: "what is the situation of election commission in Indonesia comparing with its neighboring countries". Test missing initial evidence, targeted follow-up, all scope dimensions passed to synthesis, historical-vs-current cautions and PDF/chat section overlap.
2. Unrelated question: coastal flood resilience, hospital access and housing affordability. The first answer omits subparts; the independent checker triggers a public gap search and a full rewrite, without inventing comparative measurements.
3. PDF preservation: headings, tables, body claims, source labels with dates, clickable URL annotations, absence of raw opaque citation tokens in the PDF.

The regression harness uses synthetic source text and mocked provider replies. A real authenticated staging pilot is still required to validate factual completeness and the visual PDF side by side for these two questions. Both verified CI and GHCR publication are separate gates from Render deployment and manual UAT.

## Release
Build 179.7 on architecture-v2-foundation-20261015. Expected GHCR tag after successful image CI:
`ghcr.io/transformers-enzee/bawaslu-standalone:staging-179.7`.
Do not deploy to Render until image is saved and the user replies Saved.
