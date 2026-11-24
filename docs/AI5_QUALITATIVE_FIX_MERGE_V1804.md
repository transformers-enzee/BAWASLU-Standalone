# BAWASLU v180.4 — cumulative AI-5 qualitative recovery and early QA gate

The first v180.3 Playwright full-backend run found four failures in the new regression test (2,812 other tests passed). Root cause was an integration error in the development batch: the initial engine prompt/passage and API evidence-summary blobs were not combined with the later omission-guard edits before the commit. Tests correctly detected that the runtime still ranked repeated numerical paragraphs above qualitative passages, omitted comparative evidence in the independent scope auditor, and failed to rewrite a statistics-only answer.

v180.4 composes all of these changes into the same engine and API files: qualitative source passage reservation; generic comparative analysis instructions; evidence-summary data passed to answer completeness review; and a deterministic omission guard triggering a second synthesis when covered observational sources are not cited. It retains the peer-focused search and coverage audit from v180.3 and all source-mode permissions.

The isolated-bulk GitHub workflow now explicitly runs the qualitative cross-topic regression tests as an early QA gate, in addition to the full Playwright backend and Dockerfile QA suites. Existing PDF exports and optional Research Trail appendix are unchanged. No Supabase migration, official action, or Render deployment occurs.

Branch: architecture-v2-foundation-20261015.
Build: 180.4.
Target image: ghcr.io/transformers-enzee/bawaslu-standalone:staging-180.4.
