# SmartRadar v178.0 — New AI Assistant (independent, first walkthrough)

## Scope and navigation
The **existing BAWASLU Intelligence Assistant remains unchanged** at \`/assistant\`
(Management: \`/management/assistant\`). A new product labelled **AI Assistant**
appears immediately beneath it in the Operations sidebar at \`/ai-assistant\`
and under the Management assistant at \`/management/ai-assistant\`.

The new page and the new read-only \`POST /api/ai-assistant/chat\` API are independent
of the old assistant endpoint, source-selection state, and conversation history.
The two existing dashboard workspaces remain distinct. Management Home
(\`/management\`) and its fixed, sourced executive brief are reused, not duplicated.

## Three connected workflows
- **Research and analysis:** authorised SmartRadar/formal and saved Social
  Listening records, opt-in public web/indexed social research, and authorised
  legal PDF references. Per-turn research trail includes actual consulted status,
  source type, timestamps where available, scope and missing incident location.
  Public searches receive only the current safe question, not private excerpts,
  prior AI text, access grants or uploaded files.
- **Strategy and action planning:** source-linked alternatives, benefits/trade-offs,
  suggested reviewing *roles* (not named assignments), proposed milestones, and
  review checkpoints. Nothing is legally binding or automatically assigned.
- **Drafting and revision:** editable drafts of summaries, memos and emails, with
  user follow-ups such as shortening, changing the audience and converting to
  email. Current research and prior draft context remain distinct: previous AI
  answers are not independently verified source evidence. No email sending.

**AUTO** chooses an appropriate workflow from the question. Explicit workflow
controls remain optional. A separate answer *perspective* can be AUTO,
Management (leadership-only) or Operational; it does not change source access.

## Evidence and security contract
1. All local reads use the existing officer-permission and geography-scoped
   data selectors. No new database table, privileged role or permission bypass.
2. Source status explicitly distinguishes fixed saved snapshots, live public
   URL-attributed research and unavailable sources. Demo-only fixtures remain
   simulated and are not presented as actual BAWASLU case facts.
3. Model-generated source IDs are checked against retrieved and authorised
   evidence. Unsupported IDs and citations are stripped; unsupported findings
   are clearly labelled inference. Social allegations do not become verified
   violations; public links do not become judicial findings; uploaded/reference
   PDFs do not become certified current law.
4. Repeated canonical URLs are flagged as possible duplicate sources, not
   independently corroborating cases. Missing confirmed incident location
   remains unknown. Date-window comparisons are provisional; cross-period
   population claims require complete and comparable denominators.
5. Questions containing private record identifiers or personal contact
   information are never sent to public web search. A missing named private
   record blocks case-specific synthesis rather than substituting other cases.
6. The assistant uses politically neutral, consistent standards across all
   candidates and parties and minimises unnecessary personal data.
7. All strategies, plans and formal drafts are review-only. This phase creates
   no cases, external emails, assignments, enforcement steps or approvals.

## First walkthrough
1. As an authorised officer, open the Operations sidebar. Check that **AI
   Assistant** is directly below **BAWASLU Intelligence Assistant** and that
   the existing assistant still opens separately.
2. Ask a general question (e.g. "What is an electoral violation?"). Inspect
   whether only actually consulted source categories show "Consulted".
3. Ask for a case comparison. Review claim-by-claim source references,
   possible duplicate URLs, unknown locations and uncertainty.
4. Ask for three response options and a proposed action plan. Check owner
   roles, trade-offs, milestones and review points remain suggestions.
5. Ask for a memo, shorten it, change the audience, and turn it into an email.
   Confirm the text is editable and no sending takes place.
6. From an authorised leadership role, open Management Home, confirm the
   existing executive brief, then use the separate Management AI Assistant.
7. Confirm non-leadership users cannot select the management perspective
   and that private source IDs are not forwarded to public search.

## Controlled QA
- New Python unit tests: intent selection, role and source gates, citation
  allowlist, conservative evidence classes, private-query blocking, duplicate
  URL handling and no-provider behaviour.
- New Node frontend contract checks: navigation, distinct routes,
  workflows, provenance, editor, and user confirmation protections.
- New Playwright browser tests use explicit simulated fixtures; no paid API
  or production mutations. Existing test suites and Docker build gates run.
- Version label is bumped sequentially to **178.0**.

## Deferred for the NEXT phase
This is a first implementation, not a claim of full national intelligence
coverage. Planned follow-ups: validated cross-case clustering beyond duplicate
URLs, complete provincial and time-period comparison, primary-law currentness
verification and legal-impact synthesis, structured strategic scenario
evaluation, persistent management decision approvals, and document/email
integrations. No uncontrolled social platform crawling is introduced.
Session conversations do not persist after navigating away or reloading.
