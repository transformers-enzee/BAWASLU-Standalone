# BAWASLU AI Assistant — Management + Operations Requirement Baseline (v175.83)

Status: Phase 1 staging implementation in progress; **not** a claim that phase 2 or phase 3 is delivered.

## Purpose

Two connected, role-scoped workspaces support authorized BAWASLU staff. **Management** starts with an executive command home, reviewable management brief, and management AI assistant. **Operations** preserves existing SmartRadar, Social Listening, Intelligence Inbox, officer workflows and the operational assistant. Both views read existing permission-scoped data. A management page must not grant additional source permissions or independently establish legal outcomes.

### Three workflows on one underlying evidence contract

1. **Research and analysis** — staff explicitly select: (i) saved SmartRadar / BAWASLU records, (ii) optional live public web/social lookup, (iii) authorized PDF legal/reference pages. The server must honor those opt-ins. Only source classes actually read are reported as CONSULTED. Saved database records are fixed answer-time snapshots; attributable public-web URLs qualify as a live-at-query-time lookup, not ongoing verified monitoring; demo records are simulated. Uploaded PDF pages are not certified official/current legal instruments. Findings must distinguish attributed allegations, officer-reviewed records, primary-source verification and inference. Each visible claim must carry an authorized, audit-valid source ID or be labeled unsupported.
2. **Strategy and action planning** — compare plausible nonpartisan oversight options, trade-offs and evidence gates, propose a response with suggested responsible role, deliverable/milestone and review point. No invented assignments, deadlines, approvals, legal verdicts, or targeted political persuasion. Recommendations remain decision support.
3. **Drafting and revision** — produce executive summaries, management memos and email reply drafts; allow revisions such as shorten, change audience or transform to email, retaining citations and caveats. Resolve prior substantive user topic but re-retrieve currently authorized evidence; never elevate previous AI answers into evidence. No email sent or task assigned automatically.

## Evidence and source policy

- Use permission-filtered saved formal intelligence, Social Listening and PDF passages. Only the cited record IDs actually selected may support source-dependent findings.
- Preserve original social allegations as allegations and officer relevance review as review status, not a court or violation finding.
- Cross-source count denominators must deduplicate by canonical URL/source key where possible. Reposts are not independent corroboration; missing country/province must be reported as unknown rather than inferred. Distinguish source publication, collection and validation times.
- Apply the same neutral evidentiary standard to all parties and candidates. Minimize names, handles, unnecessary author metadata and private text in executive management surfaces.
- Explicit public web is an opt-in provider research call that may spend OpenAI credits, not a SocialCrawl crawl; never send private stored evidence to public search. Public-only questions with named internal IDs are blocked.
- Official legal references: phase 1 uses authorized reference library with visible officer-review/currentness limitations. **Independent verification of current primary law and legal-impact synthesis remains phase 2.**
- A source card indicates what was selected; a citation attached to a material claim indicates the relevant support was actually cited. Neither proves source authenticity.

## Build order

| Phase | Priority | Implementation and acceptance |
|---|---|---|
| 1 | **FIRST** | Separate Management and Operations navigation/routes. Management home and sourced executive casework brief. Two AI modes (Research & Analysis, Strategy & Drafting), explicit source selection, truthful consulted-source ledger, structured source-linked observations, staff-review-only draft plans, follow-up memo/email revisions. Controlled no-credit QA, staging manual walkthrough against accessible standalone prototype. |
| 2 | **NEXT** | Cross-case synthesis across deduplicated source groups, verified geography/date basis, source reliability/provenance and legal-impact assessment. Strategy options/scenarios with trade-offs and human-approved management decision log. |
| 3 | **LATER** | Advanced operational assignments, approvals, cross-team escalation, workflow automation and monitored follow-ups. Must require explicit role checks, audit trail and human confirmation before any external action. |

## First walkthrough — acceptance conditions

- [ ] Management and Operations routes are separate, with permission-scoped navigation and no production changes.
- [ ] Management home opens as read-only, shows current authorized casework window and evidence limits; empty casework is not mislabeled absence of events.
- [ ] Research mode: choose one source at a time; no unselected source content appears. Status distinguishes consulted, selected but not consulted and not selected. Public URLs only if genuinely retrieved.
- [ ] Strategy & Drafting: given 2-3 controlled synthetic, cited records, compare options and propose review role, output/milestone and evidence gate. All remain drafts.
- [ ] Revision: shortening and email follow-up retains underlying source topic and uncertainty; no previous assistant text is promoted as verification.
- [ ] Cite-only allowed IDs. Invalid references removed; unfounded inferences identified.
- [ ] Simulated/fictional cases are explicitly labeled. Sensitive personal details unnecessary for the task are not surfaced.
- [ ] Backend/frontend automated tests pass in Docker; the exact image digest is published and separately verified.
- [ ] Human staging walkthrough passes. No AI/provider credits used for the controlled automated tests.

## Deferred topics

Management decision tracking with persistent owners/approvals, authoritative legal-source currentness checks, automated external web/social connectors beyond opt-in web search, cross-case and geographic time-series metrics, and task automation are **not** delivered by phase 1.
