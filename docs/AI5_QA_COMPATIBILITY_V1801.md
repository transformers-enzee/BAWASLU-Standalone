# BAWASLU v180.1 — Full QA reconciliation for AI-5 evidence-led research

v180.0 implemented dynamic outcome-first research, follow-up search, verifiable source-selection tracing, relevant read-page passages, deterministic caveat-figure recovery and opt-in PDF Research Trail. The initial isolated backend suite passed, but the comprehensive Playwright backend and frontend suites reported failures:

- Legacy AI-4 build test used a hard-coded regex admitting versions 179.4–179.9 only. Replaced this with a numeric minimum-version contract so AI-4 remains enabled for v180.1 and beyond.
- Old AI-5 PDF test always expected a Research Trail appendix. It now opts into the appendix, preserving the new user-facing default of an uncluttered main report without a near-blank audit-only final page.
- Old AI-5 export failure test mocked a three-argument export function. API now retains that interface when appendix not requested and passes the new option only when explicitly enabled.
- Old single-topic web fixture assumed exactly two web tool calls. The audit may make one additional targeted call when it cannot establish coverage; the test checks the discovery/freshness requirement and bounds at most one gap lookup without enforcing a parallel execution order.

No production, Supabase schemas or officer casework data were touched. v180.1 is staging-only on `architecture-v2-foundation-20261015`. The audited source artifact is the four-page pilot PDF; no historical original provider trace was embedded, so old search queries and passages cannot be reconstructed from that PDF. Regression tests replay the pilot question and an unrelated broad question with synthetic evidence and inspect the chat/PDF content boundary. The authenticated live provider answer/PDF still requires staging UAT after deployment.

Target GHCR image: `ghcr.io/transformers-enzee/bawaslu-standalone:staging-180.1`.
