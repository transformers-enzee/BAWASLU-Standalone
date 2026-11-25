# BAWASLU v183.6 — Assessment QA Workbench

## Scope and safety
Staging-only, opt-in, nationwide National Administrator access; keep disabled elsewhere. The backend refuses all requests unless `BAWASLU_ASSESSMENT_QA_ENABLED=1` and the user has an active Nationwide National Administrator grant and the administration permission.

Path: `/administration/assessment-qa`. Entry point: Administration > AI Assessment Framework QA.
Backend endpoints: `GET /api/intelligence-assessment-qa/catalog`, `POST /api/intelligence-assessment-qa/evaluate`.

No real sources, live AI calls, crawlers, stored predictions, Supabase writes, officer corrections, training, or Command Centre changes. This QA feature deliberately does NOT imply the v1 intelligence assessment contract has been connected to the production AI extraction pipeline.

## Manual QA sequence
1. Open staging as a National Administrator with the feature enabled. Confirm 10 field groups, 15 insights and 8 synthetic cases appear.
2. For each case, click "Compare predictions" using the default deliberately wrong synthetic sample. Expect at least one mismatch for cases 1–7.
3. Click "Load passing reference" and compare. Expect all sampled fields to match; this validates the evaluator only, NOT model accuracy.
4. For case 8, compare. Confirm AI predicted value stays `money_politics`; unapproved correction does not supersede it; approved simulated correction changes effective value to `other_regulatory_issue`. No persistence.
5. Delete a required key from a JSON submission. Expect MISSING and reduced coverage. Enter invalid JSON; expect an error. Insert a non-contract field or nested object; expect HTTP 422.
6. As a user without the national administrator grant, verify the endpoints return HTTP 403. With feature flag disabled, authorized requests return HTTP 404.
7. Confirm there are no real officer records created or altered, no AI usage consumed, and no Command Centre effect. Existing historical QA lab should continue to work.

## What comes next
Develop a strictly controlled real-model adapter (opt-in, budget-capped, server-side permissions) for a curated synthetic holdout, with AI predictions tagged separately from reviewer-approved labels. Then build persistent field-level override proposals, approval, transaction-safe audit history and downstream effective-value projection. None of those are implemented by this batch.

## Build and version
Release target v183.6. Backend `pytest -q`, frontend `npm run build` (now includes `test-intelligence-assessment-qa-v1836.mjs`), existing staging Docker workflow on `architecture-v2-foundation-20261015`. Do not deploy until QA/image pass; use immutable image by full SHA after verification.
