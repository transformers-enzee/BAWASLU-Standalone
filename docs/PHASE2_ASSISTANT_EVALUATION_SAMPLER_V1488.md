# BAWASLU v148.8 — Permission-scoped AI Answer Evaluation Question Preparation

**Scope:** Staging only, architecture-v2-foundation-20261015. No database migration or external provider calls.

## Purpose

v148.7 provides browser-local consolidation of genuine officer answer reviews, but cannot independently produce a human-scored evaluation dataset. The next prerequisite is selecting diverse **real saved source posts**, recording coverage gaps, and preparing suitable evaluation questions without calling an AI provider automatically.

## Delivered

- `GET /api/assistant-evaluation/questions?target=24` is authenticated and requires `view_intelligence`. It reuses the cached, permission-scoped, relevance-filtered Inbox findings already used by Command Centre and reporting.
- The endpoint derives a deterministic convenience sample of up to 30 distinct source-linked questions, deduplicated by original social post across linked campaigns.
- Categories: potential-violation signal, public concern, emerging narrative, geographic/jurisdiction uncertainty, platform-policy check, cross-module comparison and general saved-source review.
- Only records with a valid canonical social source ID, saved relevant Inbox inclusion and an original HTTP(S) URL are eligible. No post body is returned. Each question names its exact permitted `SOCIAL-<id>` for later verification.
- Missing category coverage, source URL omissions and any shortfall from the target are explicitly shown. A separate `SOCIAL-0` no-evidence control is tagged **not a real case** and excluded from the total.
- The selected question is loaded into the existing AI Assistant input in **DATA** mode. It is not sent until the officer clicks **Send**. The sample itself uses no OpenAI credit and launches no social crawl.
- Optional officer-initiated JSON export includes only the selected question IDs, original URLs, category, limits, warnings and control. Treat the file as access-restricted evaluation material.

## Exact source-ID guard

`assistant_orchestration._social_select` now recognizes explicit bracketed `SOCIAL-<numeric ID>` references and selects only those IDs **within the previously authorized and relevance-filtered campaign Inbox rows**. A nonmatching or unauthorized source ID yields no selected social posts; the route must not substitute a general GPT answer for that exact-ID question.

An explicit ID is **not** authorization: it cannot cause a record from another jurisdiction or campaign to be queried or included. Actual assertions remain unverified; exact ID matching is only retrieval integrity.

## Explicit limitations

- The visible questions are a deterministic **diversity-oriented convenience sample**, not a random sample or a census. Inbox reads are bounded to an existing up-to-300-links-per-authorized-campaign window; truncation and total completeness are unknown.
- A zero in any category does not establish the absence of public complaints or violations in a province.
- Category flags are saved assessments, not legal verdicts or verified events.
- A prepared cross-module question does **not** prove that a matching formal Inbox record exists; the Assistant must state when none is retrieved. The sampler does not independently match formal records.
- Officer-reviewed legal PDF questions remain a missing track until authorized officers verify and approve the documents. Legal currentness is not supplied by the sampler.
- The questions remain **unanswered** until manually submitted. They do not create human grades or count toward acceptance; later genuine answers require independent reviewer scoring and adjudication.
- No Supabase writes, new tables, new crawls, new collections, background AI, paid API evaluations, production push, or automatic legal conclusions.

## Release acceptance

1. Backend pure tests: source ID/URL validation, campaign deduplication, target bounds, candidate diversity, sample shortfall, metadata/no-raw-post privacy, no generated legal claims.
2. Exact source selection tests: authorized exact post returned despite unrelated text; unauthorized, irrelevant or nonexistent IDs not substituted.
3. Auth endpoint: permission denied before source fetch, no-store headers.
4. Browser: review panel is opt-in, fetch occurs on click, prompt selection does **not** invoke the Assistant, DATA mode and source ID persist, source restrictions can be enforced, JSON download works.
5. Existing frontend build, PostgreSQL security, version monotonicity, offline assessment and full backend/browser suites must pass; Render must show the exact v148.8 commit as LIVE.

## Next required human milestone

Qualified officers must select and review representative genuine sources, **manually run** the prepared questions, export the resulting answer packets (v148.6), score independently (v148.7), and adjudicate disagreements. No scored answer or acceptance is claimed by this release.
