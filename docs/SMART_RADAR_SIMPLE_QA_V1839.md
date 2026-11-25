# BAWASLU v183.9 — Simple AI Assessment Testing Centre

## Scope
This release replaces the technical default QA screen with a plain-language, scenario-based flow while retaining original JSON diagnostics at `/administration/assessment-qa/diagnostics`.

On the main page, a national administrator chooses a synthetic post, reads expected observations, clicks **Preview example (free)** or **Run actual AI assessment**, and sees clear matched/missing/wrong findings plus a proposed officer verification step. Local "Looks acceptable" or "Needs improvement" feedback is UI-only, not persisted or used as training labels.

## Safety and access
The existing flag `BAWASLU_ASSESSMENT_QA_ENABLED=1` allows national administrators to access the workbench; the second flag `BAWASLU_ASSESSMENT_QA_LIVE_AI_ENABLED=1` controls paid live AI separately. **Paid mode defaults OFF.**

Live QA:
- Accepts only an eight-case server-owned synthetic ID, never free-form user text, officer records, credentials or source URLs.
- Uses the existing configured QA OpenAI model and API key, no web search.
- Runs only after an explicit browser confirmation on the named scenario. Case 8 officer override remains offline because it is a deterministic correction-precedence test.
- Reserves a budget slot in the existing append-only `audit_events` table before every provider call, protected by a PostgreSQL transaction advisory lock to prevent concurrent overrun.
- Defaults to 3 reserved calls per UTC day and a total lifetime of 24. Optional limits `BAWASLU_ASSESSMENT_QA_LIVE_DAILY_LIMIT` (hard maximum 8) and `BAWASLU_ASSESSMENT_QA_LIVE_TOTAL_LIMIT` (hard maximum 24) can lower those limits. Invalid or zero values fail closed. Missing PostgreSQL, API key or any disabled flag blocks paid calls. Failed provider requests still count against the reserved allowance.
- Caps model completion to 650 tokens and returns source-traceable predictions, summary, recommended verification step, model name and usage.
- Does not save predictions, modify source/casework/Command Centre rows, train models or mark legal violations proven. Only QA budget-reservation audit entries are persisted.

**Important limitation:** Live QA exercises the configured QA model on fictional text using the assessment data contract. It is NOT yet an end-to-end test of production Social Listening collection, actual Inbox assessment prompts, RLS for real evidence or the Command Centre aggregation engine. The reference answers are illustrative, not adjudicated gold. A comparison mismatch is for analyst review rather than automatic training feedback.

## Manual QA
1. Open the staging QA URL as an active Nationwide National Administrator.
2. Case 1: click "Preview example (free)" and verify the planted incorrect allegation status is highlighted in natural language.
3. Repeat 2 for cases 2–7. Case 8: "Test correction rules (free)" and verify only approved overrides take precedence.
4. Open Developer diagnostics to confirm the prior technical screen is preserved.
5. In a staging service only, enable the second live-AI flag and set a low global budget, then explicitly confirm one real-AI test. Expect model name, summary, officer check, field-level differences and reduced allowance.
6. Verify unauthorized access is denied, disabled mode refuses paid calls, no real source records change, and the QA audit record is created only when a paid attempt is reserved.

## Release
Target v183.9. Run existing Python suite and frontend contract/production build. Publish an immutable GHCR tag based on full commit SHA after CI passes. Do not automatically change an existing Render image deployment.
