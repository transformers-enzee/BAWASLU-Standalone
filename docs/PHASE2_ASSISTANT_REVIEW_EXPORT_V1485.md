# BAWASLU v148.5 — Human Answer-Quality Review Packet Export

**Release note:** v148.6 corrects stale version-specific assertions in the v148.4 and v148.5 regression scripts. The v148.5 review-export capability and security boundaries are unchanged.

**Environment:** staging only, architecture-v2-foundation-20261015.
**Purpose:** Make the human review of genuine Assistant question–evidence–answer examples reproducible without inventing model accuracy, legal clearance or officer approval.

## What officers can do

For a freshly generated AI Assistant reply that includes the v148.4 quality-check panel:

- Click **Export review evidence (.json)** to capture the exact question, response (up to 100,000 characters), authorized source-card IDs and capped excerpts, displayed citation identifiers, four automated checks, language and response profile. Packet includes a stable **noncryptographic** identifier for matching to the CSV (it is NOT tamper-proof).
- Click **Export blank scoring sheet (.csv)** to obtain four rubric rows: citation grounding, topical source relevance, legal uncertainty, cross-module consistency. Every human_score_0_1_NA, evidence_reference, reviewer_note, reviewer_id and reviewer_date_utc field is **empty**.
- Reviewers complete their own 0/1/N/A ratings and evidence notes. A second reviewer may adjudicate disagreements outside the system. This release does not claim or store official sign-off.

Both exports happen in the browser **only following an explicit button click**. No network upload, paid AI call, background activity, Supabase table or new approval route. The JSON contains source excerpts; handle in authorized secure storage, not public issue trackers. URLs are limited to HTTP(S). Arbitrary source/private attributes (API tokens, non-whitelisted fields, hidden notes) are excluded.

## Scope and access protection

This control is available **only for replies generated in the current authenticated Assistant page session**, not for historical conversations reopened from stored chat history. Prior permissions may have changed after a response was saved. Re-run a historical question to obtain a fresh permission-scoped answer before exporting.

The local export copies the source cards already delivered to the user; it does not independently requery the database at export time. The JSON states source_permissions_rechecked_at_export=false to prevent accidental claims of a new access check.

The evidence list is capped at 25 records; source excerpts at 600 characters; the packet clearly flags any truncation. The text is capped at 100,000 characters and separately flags truncation. These bounds prevent unexpectedly large or sensitive files from being silently exported.

## Review packet contents

- schema_version BAWASLU_ASSISTANT_REVIEW_V1485, packet ID, export timestamp and build version
- question, assistant answer, response profile, language, model identifier/mode when available
- selected authorized source-card records with type, title, excerpt, URL, platform, timestamp, sentiment, document page and review status
- displayed cited IDs and the four rule-based auto-check statuses
- human_scorecard with all four rows **blank** and reviewer/adjudicator identity fields empty
- explicit human_accuracy=null, human_gold_answers_evaluated=0, officer_approved=false, legal_findings_confirmed=false

## Recommended actual reviewer workflow

1. Use at least 20–30 distinct, representative BAWASLU Assistant questions. Include provincial restrictions, suspected violations, public concerns, actor narratives, PDF guidance, policy-vs-law distinctions, and no-evidence cases.
2. Ask each question in the authenticated **staging** Assistant. Inspect the original source links; export the JSON and CSV immediately from the new response.
3. Two qualified officers independently score each of the four dimensions in the CSV. Cite exact source IDs/pages and state their reasoning. Use 0 (incorrect/unsupported), 1 (supported/correct), or N/A.
4. Adjudicate disagreements, note uncertainty explicitly, and retain the question, answer, evidence packet and scoring sheet together under the same packet ID.
5. Compute dimension-level agreement and accuracy **only after** genuine human labels exist. The v148.4 16 synthetic fixture tests do not contribute to that denominator.
6. If a cited PDF is not officially reviewed or its current legal force is unknown, record the limitation; do not approve legal advice based on an automated quality flag.

## QA and release gates

- Node contract test verifies privacy-by-allowlist export, blank human scores, known AI warnings, matching packet IDs, CSV safety, capped source snapshot and explicit lack of approval.
- Playwright test checks both download buttons, JSON content and CSV blank scoring rows.
- Full staging CI (backend, frontend, security, offline contract, version monotonicity, browser QA) must pass; the exact commit must be live on Render.
- Genuine BAWASLU answer-quality acceptance is **still pending**; this feature prepares the reproducible review materials.

This implementation uses zero paid provider credits during automated QA, creates no actual officer case, and changes no production environment or Supabase data.
