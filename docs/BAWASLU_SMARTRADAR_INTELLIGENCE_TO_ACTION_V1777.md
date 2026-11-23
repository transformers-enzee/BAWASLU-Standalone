# BAWASLU SmartRadar v177.7 — Intelligence-to-Action Assistant

## Why this release
The v177.6 public-web-only path returned a readable report but always returned
`decision_plan: []`. That prevented concrete follow-up tasks from appearing
on the default web-first assistant, even when source evidence was relevant.

## Implementation
1. Public web research retains its existing fail-closed private-ID filter, source
   URL allowlist, runtime limits and retrieval timestamp.
2. An optional second AI call transforms only the returned **public** research
   summary and up to six attributable HTTPS sources into a strict JSON
   institutional assessment. It never receives saved SmartRadar data, attachments,
   users, personal identities, secrets or conversation history.
3. The decision sanitizer rejects unconsulted citation URLs, downgrades claims
   falsely labeled as primary-source supported, and rejects unsafe or incomplete
   tasks. Legal applicability is always human-review-required.
4. A public claim on a government website is **source-reported**, not a judicial
   finding or independently officer-authenticated fact. Only official legal
   document URLs can provisionally support the claimed controlling provision.
5. Decisions distinguish `DIRECT_OVERSIGHT`, `POSSIBLE_NEXUS` and
   `NO_ESTABLISHED_NEXUS`. A direct claim without a traceable mention of
   election-supervision responsibilities is downgraded for review.
6. The UI shows BAWASLU relevance, proposed decision, verification tasks, reviewer
   roles, evidence to obtain, deliverables, and escalation/closure gates.
   Separate details show law, institutional responsibilities and platform policy.
   Full source provenance and claim classification remain in Research Trail.
7. Fresh authorized answers permit **copy action plan**, **download review-only
   JSON packet** and **draft leadership memo**. No automatic assignment,
   enforcement, complaint, external sending or legal determination occurs.
8. The existing owned conversation history stores only bounded snapshots,
   including the WEB_RESEARCH profile and proposed decision data. Saved answers
   have a historical caution; past review actions require a new current check.

## Evidence and legal boundaries
- Priority sources: relevant official legislation and institutional records;
  media provides attributed leads, not legal conclusions.
- BAWASLU's election supervision, DKPP's ethics review, KPU administration,
  MPR succession and platform moderation are different authorities.
- Election type, stage, incident location, actor role, controlling text,
  effective date, and procedural thresholds are verified by a competent officer.
- Criticism, sentiment, reposts or allegations never establish wrongdoing.
- A no-jurisdiction conclusion may properly recommend **no formal action**.
- No false 14-day trend conclusions from shorter or different samples.

## QA and release
- No-cost Python tests cover source URL validation, illegal action rejection,
  no-nexus behavior, primary-law availability, incomplete-search fallback,
  stored historical review snapshots and JSON schema.
- Source-contract frontend test covers visible officer cards, source detail,
  live-user actions, guards, and audit/research panels.
- Both frontend and backend build versions equal **177.7**.
- GitHub Actions frontend build, backend bulk QA, Playwright, image publication,
  security and release contract must all succeed before handing off the image.

## Manual live-answer acceptance
Test the following on staging (do not use invented current claims):
1. **Recent Gibran discussion** — the direct answer identifies whether an
   official DKPP/BAWASLU oversight nexus is evidenced. It recommends a
   source-linked institutional verification task with role, evidence, output and
   decision gate; it does not treat succession itself as BAWASLU jurisdiction.
2. **Opinion-only criticism** — no case action without lawfully relevant conduct,
   jurisdiction and corroboration.
3. **Unverified social-media allegation** — distinguishes reporting from a finding;
   identifies official law/source needed and the competent reviewer.
4. **Legal question** — names only directly supported controlling provisions and
   clearly states unverified applicability, election type/stage and institutional
   authority.
5. **Leadership strategy** — compares proportionate options and states what new
   evidence would change the recommendation.
6. **Draft** — drafts the requested output first, preserves citations, and leaves
   all sending/approval to authorized humans.
7. **Offline public web** — no fabricated current findings, conservative review
   action, and explicit research gap.
8. **History reload** — new officer action cards remain viewable as a dated
   snapshot but cannot initiate privileged casework from stale source access.

## Known limits
- The second call adds inference latency and API token consumption; if it fails
  the endpoint returns the original web brief plus an explicitly labeled,
  conservative verification step rather than fabricating case facts.
- The model's action synthesis is an **unapproved recommendation**, not a
  verified law-finding. Live answers require officer review and follow-up.
- This release reuses the existing permission-scoped assistant and chat history.
  No new persistent task assignment table or external workflow execution is
  introduced.
