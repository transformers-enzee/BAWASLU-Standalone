# BAWASLU v148.9 — Exact-Source Evaluation Guardrails

**Environment:** Staging branch \`architecture-v2-foundation-20261015\` only.
**Release:** One bulk commit. Supabase schema and data are unchanged; no paid AI or crawl is initiated by this release.

## Why this follow-up is needed

The v148.8 Assistant question sampler creates exact saved-source questions for human evaluation. A comparison may name two original Social Listening IDs, or the special no-evidence control \`[SOCIAL-0]\`. Retrieving only one of the requested IDs and allowing unrelated formal records or PDF passages to answer it would produce a misleading review packet. A passing citation check alone does not establish that the requested source was retrieved.

## Delivered

1. Source selection is all-or-nothing for explicit \`SOCIAL-<numeric ID>\` references. The system must retrieve **every** named, authorized, relevant, non-empty saved post; otherwise no social post is selected.
2. More than 20 explicit IDs fail closed, rather than silently truncating a comparison and creating a partial answer.
3. For an explicit-ID question with a missing or inaccessible source, the v2 Assistant clears unrelated formal and PDF evidence and returns the existing deterministic no-match response. The AUTO and GENERAL paths cannot replace a missing named post with general-model prose.
4. Evaluation sampler original URLs reject embedded whitespace, control characters, backslashes, missing hosts, embedded credentials and non-HTTP(S) schemes.
5. Python regression cases cover comparisons, inaccessible and irrelevant IDs, 20-source bounds, the no-evidence control, and URL hygiene. Frontend static build checks enforce the fail-closed route and matching API/UI release versions.

## Boundaries

- Exact ID matching validates **retrieval identity**, not the truth of source allegations, suitability of citations or legal validity.
- Only existing permission-scoped saved Inbox evidence is eligible.
- The missing-source response intentionally does not disclose whether an ID is absent globally, inaccessible due to a role/jurisdiction, or excluded as irrelevant.
- No new human ratings, genuine officer approvals, approved legal PDF assessments, Supabase migrations, or production releases are claimed.

## Verification and acceptance

Run the full backend suite, frontend build checks, Playwright suite, PostgreSQL/security offline check and build-version contract against the same commit. After CI, independently verify Render staging is LIVE at the exact commit hash. Human answer scoring, casework and legal-document review remain separate acceptance gates.
