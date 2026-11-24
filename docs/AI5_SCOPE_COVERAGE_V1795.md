# BAWASLU v179.5 — AI-5 scope-preserving General Research

## Root cause and correction
Before v179.5, AI-5 submitted the whole question to a single web-search discovery pass (plus a freshness pass for recent topics), then retained the first eight URLs. There was no audit for dimensions omitted by discovery or unreadable pages. Source eligibility remained strict but could not compensate for absent evidence.

This batch introduces a general-topic, strict-JSON research dimension planner, parallel dimension-specific discovery, round-robin candidate selection, a readable-excerpt coverage audit, targeted gap searches, and a final coverage report passed directly into synthesis. Source limits are now a bounded 12 initial + 6 follow-up pages, respecting safe HTTPS reading. Failed planning/auditing is conservative and does not mark missing snippets as verified evidence. Recent-date corrections remain supported.

## General Research response contract
Start with a useful finding, explain contextual meaning, and address every part of the question. Compare sources quantitatively when metrics are comparable, qualitatively where populations, time periods, definitions or measures conflict. Explicitly name partial and missing dimensions. Answer in the question's language. Use original source titles in inline links; retain source IDs in the audit and exports. BAWASLU operational/management advice remains behind **Use for BAWASLU**.

## Trace surfaces
The authenticated research trail displays planner dimensions, search requests and provider query metadata where reported, discovered lead counts, coverage status, source titles, which readable sources were forwarded to the model and IDs cited in the final body, draft and table. The page list records read status and publication metadata. Private saved records remain excluded in WEB_ONLY, and no model-generated URL becomes a verified source.

## Automated tests
- Solar versus wind: costs, reliability, environmental effects — ensures missing environmental evidence initiates targeted search and contributes a readable source to synthesis.
- Coastal cities: flood protection, public health, housing affordability — ensures the outstanding housing gap remains explicit after follow-up.
- Round-robin source allocation avoids early-result monopolization.
- Unreadable snippets cannot satisfy coverage.
- Model synthesis prompt retains complete scope and allows qualitative cross-metric comparisons.
- Existing AI-5 test contract still runs in Docker QA.

The tests are deterministic and mocked; they do not replay an unavailable original AI-5 user attachment or prove the live provider's final prose quality. On staging, a user should replay that original question plus the unrelated case and examine the research trail/answer before signing off.

## Staging release
Branch: architecture-v2-foundation-20261015. Docker build: 179.5. GHCR image tag (if CI publishes): `ghcr.io/transformers-enzee/bawaslu-standalone:staging-179.5`. Do not modify production or Supabase schemas. Render image selection remains manual.
