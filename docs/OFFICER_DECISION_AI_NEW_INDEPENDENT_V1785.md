# Officer Decision AI — independent new assistant (v178.5)

## User-defined source specification
Implementation is based on the uploaded *SmartRadar AI Assistant — Proposed Intelligence-to-Action Upgrade*. This is an intentionally independent third assistant, not an iteration of either old assistant's prompts, history, UI, retrieval functions, schema, or generative response pipeline.

## New module boundaries
- UI: `frontend/src/pages/OfficerDecisionAssistant.jsx`
- Server: `backend/app/officer_action_v3/`
- API: `POST /api/officer-decision-ai/analyze`
- Routes: `/ai-assistant-v2-new`, `/management/ai-assistant-v2-new`
- Navigation: **AI Assistant V2 · New** directly below the old two assistants.
- Shared platform dependencies **only**: authorization, scoped IntelligenceItem readers, database connection, and approved OpenAI provider environment variables.
- No old assistant imports, chat-history lookup, prior AI answer content, conversation persistence, previous drafts, or old source-selection contract.
- Starts from one current question per request; does not inherit conversation state even across uses of the new page.
- Staging-only GitHub branch; no migrations, source mutations, assignments, referrals, messages or emails.

## Six distinct capabilities
1. **Research & Evidence:** Independent OpenAI `web_search` with compulsory actual search action. Discovery in Bahasa Indonesia and English, latest-update checks for developing stories. Opens returned public HTTPS pages with public-DNS and resolved-peer checks, no redirects, bounded pages/bytes/time, and read-state audit. Readable source text is fed into one fresh synthesis prompt. Web only sends the question, never private source text.
2. **Claim verification:** Rejects hallucinated source IDs, separates `PRIMARY_SOURCE_REPORTED`, `INDEPENDENTLY_CORROBORATED`, `ATTRIBUTED_ALLEGATION`, `CONFLICTING`, `INFERRED`, `UNRESOLVED`. Corroboration requires distinct read public-source hosts. Saved snapshots never count as independently authenticated.
3. **Legal and institutional jurisdiction:** Builds a provisional competence matrix for BAWASLU, KPU, DKPP, MPR, Gakkumdu, Polri, Komdigi and platform rules. Exact current legal provision and applicability always require authorized human legal review; no presumption that online criticism is a violation.
4. **Officer decision and action:** Structured recommendation with up to three tasks, reviewer role, evidence required, deliverable, and escalation/closure gate. Review-only; nothing is assigned or filed. **No formal action** remains a valid outcome.
5. **Answer-first UI:** Main finding, institutional implications, actionable cards, editable downloadable evidence matrix/legal brief/action plan/memo; expandable Research Trail for source titles, dates, read statuses, detailed legal questions, options, limitations and audit. No case-form default.
6. **Quality gate:** Checks source IDs, demotes unsupported assertions, limits repeated actions, excludes automatic enforcement and unconsulted hyperlinks, refuses to invent facts without evidence, and marks all legal conclusions and plans as subject to approval.

## Source modes
- Web only — public web before synthesis; no saved records read.
- Web + SmartRadar — public web first, then permission-scoped direct source snapshot reads.
- SmartRadar only — no external public query. Can inspect authorized saved snapshots but they are **not** current corroboration.

The provider status is disclosed up front if live research is unavailable or no opened pages are readable. Page statuses are `READ`, `SNIPPET_ONLY`, `INACCESSIBLE`, `SAVED_SNAPSHOT`.

## Honest limitations and future stages
This is an independent staging foundation, not a complete legal case-management product. Automated version-aware legislative consolidation, platform-specific moderation policy retrieval, multi-platform historical sentiment measurement, independent attachment ingestion, persistent officer workflow approvals and live external provider acceptance need later, dedicated verification and governance. The system expressly does not assert that it has performed those operations.

## Automated tests and release gate
- `backend/tests/test_officer_decision_v1785.py`: authorization, privacy, prompt isolation, safe URLs, source/read audits, claim attribution, legal uncertainty, no-evidence fallback, web-only nonretrieval, saved-only no web.
- `frontend/scripts/test-officer-decision-v1785.mjs`: independent routes, page, API, engine modules, QA contracts and Docker version.
- `frontend/e2e/officer-decision-v1785.spec.js`: logged-in officer navigation, response rendering, attributable public citations, work products, exact source-mode API payloads and fresh state.

Full repository tests, frontend build, browser tests and published Docker release must pass before handing over an image.

## Live acceptance after Render source update
1. Log into the staging site; select **AI Assistant V2 · New** beneath existing assistant(s).
2. In Public web only, ask "What is the latest official BAWASLU or DKPP development this week, and what should the officer do next?" Verify the actual read-page dates, currentness, official jurisdiction, direct conclusion and work product.
3. Review the expandable Research Trail. Check that any blocked, snippet-only or inaccessible page is not cited as if opened and read.
4. In Web + SmartRadar, use an authorized relevant internal topic, then check distinct public and internal source labels; try Web only again and confirm saved snapshots are absent.
5. Ask a constitutional succession question: jurisdiction should not automatically be assigned to BAWASLU. Ask an allegation question: no automatic violation, referral or punitive action.
6. Ask for a leadership memo; confirm draft-first presentation, copy and editing.
7. Verify that neither previous assistant's histories or saved conversations appear, and that no task, case or email was created.

Successful mocked offline QA must not be presented as a real live-page research validation.
