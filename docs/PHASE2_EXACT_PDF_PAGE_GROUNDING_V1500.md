# BAWASLU v150.0: Exact PDF Pages and Complete Overview Grounding

## Reliability gaps
A human can explicitly cite a BAWASLU AI reference page such as DOC-123-P2. The prior lexical/hybrid lookup was not an identity lookup and could choose a different page when those numeric identifiers did not match indexed terms. Similarly, broad PDF overviews sampled the first chunk of each chosen page, losing later text in the same citation.

## Changes
- An explicit DOC-<id>-P<page> identifier routes to PDF_GUIDANCE, including when AUTO or GENERAL would otherwise select generic knowledge.
- Resolve only exact pages from currently active, permission-scoped uploaded documents. If any requested page is inaccessible, withdrawn, unindexed or missing, **return no PDF evidence**; never substitute another page or general GPT knowledge.
- Read all indexed chunks for each requested page, stitch them into one bounded cited excerpt and retain the exact document/page ID.
- Broad PDF document-overview answers now stitch all selected page chunks, still sampling a small number of pages across up to two visible documents.
- Keep document review and legal currentness distinct. Officer-reviewed metadata alone is not a currentness or legal verdict.
- No new schema, Supabase writes, crawling, model evaluation, paid embedding request or server authorization changes. Tests exercise cross-province isolation, withdrawn documents, missing pages, oversized requests and complete overview text.

## Release gates
Run backend, frontend, browser, security, version CI and verify that Render's staging deployment points at the exact commit. Genuine officer PDF approval and answer-quality acceptance remain separate pending human gates.
