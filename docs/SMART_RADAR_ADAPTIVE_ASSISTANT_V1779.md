# SmartRadar v177.9 — Adaptive Research, Strategy & Drafting

## Purpose
One permission-scoped assistant supports open-ended research, legal explanations,
case comparisons, strategic options, action planning, and drafting without a
required Research/Strategy switch. Management and Operations remain separate
authorized workspaces, not separate source silos.

## Delivered in this commit
- Auto task style routes ordinary questions to research and requests for plans,
  strategies, memos, reports, emails, summaries and revisions to staff-review-only
  drafting support. Manual workflow selection is still available.
- The assistant selects authorized SmartRadar records, public web, legal/reference
  library and conversation attachments by default. Users can deselect any source.
  Source-consultation metadata still identifies which sources were actually used.
- Live public research can answer general or legal questions when no matching
  saved evidence is present, rather than responding that no saved record exists.
  Named private identifiers remain blocked from public queries and unavailable
  saved records never turn into fabricated citations.
- A common Research & Productivity title and revision shortcuts support flexible
  follow-up questions in either workspace.
- No automatic mail sending, legal verdicts, officer assignment, case creation
  or external enforcement actions are introduced.

## Constraints / remaining work
- Public social research is limited to attributable web results or existing
  authorised provider crawls. This release does not create unrestricted direct
  access to every social platform or a new social crawl provider.
- A selected source category does not guarantee source results. Web calls
  require configured OpenAI API credentials, supported web_search and network.
- Full editable DOCX/PDF export, authorised email sending, decision approval
  and new proactive background monitoring remain separate developments.
- Model-written draft text and plans remain proposals requiring human review.
- A push to the Git source branch is not itself a release of the separately
  published staging container. Validate CI, publish and deploy exact image
  only after release checks.

## Automated QA gates
- New zero-provider-cost Python adaptive-intent/safety tests run in the Docker
  build, alongside existing assistant regression tests.
- New Node source-contract test runs before the Vite build.
- Existing web-first and assistant-workspace compatibility contracts are kept.
- Increment build label from 177.8 to 177.9 for this bulk change.
