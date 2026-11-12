# BAWASLU Phase 2 - Human Answer Review Consolidation (v148.7)

Environment: staging only, architecture-v2-foundation-20261015.
Scope: local, officer-initiated aggregation of genuine AI Assistant answer-quality reviews. This does not evaluate the model by itself.

## Prior state

- v148.4: four deterministic diagnostic checks and sixteen synthetic test cases; these do not constitute an AI accuracy benchmark.
- v148.6: manually downloadable JSON question-answer-evidence packets and CSV blank human scorecards. No officer ratings or legal approvals were manufactured.
- Real acceptance: zero human-scored cases independently verified by the system. Real casework acceptance and review of legal PDFs remain separate.

## Delivered

A collapsed **Human answer-review consolidation** section in the existing AI Assistant lets an authenticated officer select multiple local JSON packets and completed CSV scoring sheets. No files leave the browser and no database records are created.

The importer:

1. Requires the JSON packet manifest BAWASLU_ASSISTANT_REVIEW_V1485 and validates its four dimensions plus the noncryptographic ID derived from the question and answer. This detects accidental mismatches; it is not a signature and cannot authenticate content or identity.
2. Supports the original eight-column v148.5 CSV and adds three optional columns to newly exported scorecards: adjudicated_score_0_1_NA, adjudicator_id, adjudication_note. Each scoring CSV must contain exactly the four rubric rows and match a selected JSON packet.
3. Counts a score 0/1 only after two distinct, self-declared human reviewers score the same packet/dimension and agree, or after a documented third-party adjudicator resolves a disagreement. An adjudicator may not be either reviewer. Duplicate uploads from the same reviewer are not counted as two reviews.
4. Keeps absent scores, missing JSON packets, conflicting reviewer sheets, extra or ambiguous reviewers, and unadjudicated disagreements out of the scored denominator. N/A is tracked separately and excluded.
5. Shows per-dimension scored numerator and denominator, score=1 support ratio, reviewer agreement and outstanding workload. The support ratio must not be represented as certified model accuracy.
6. Allows export of a minimized aggregate JSON containing only packet IDs, rubrics, counts, statuses and correction warnings - never raw question text, Assistant answer, original source excerpts, reviewer names or private review notes.

The import checks citation_grounding, source_relevance, legal_uncertainty, and cross_module_consistency.

## Scoring and adjudication instructions

- Each independent reviewer receives the relevant packet and a separate copy of the scoring CSV.
- For each dimension, fill human_score_0_1_NA with 0 (unsupported/incorrect), 1 (supported/correct) or N/A. Include reviewer_id, valid review_date_utc, and reviewer_note of at least 12 characters. A scored 0/1 also requires an exact evidence_reference.
- For a disagreement, a third, different adjudicator completes the optional adjudication fields for that dimension (score 0, 1 or N/A, adjudicator ID and explanatory note).
- Select the JSON packet and reviewer CSVs together in the consolidated review file chooser. A single-reviewer row remains incomplete. Two agreeing scores become a reviewed consensus. Disagreements remain unresolved until adjudication.
- Inspect the original source and any legal-document currentness separately before accepting a finding.
- Retain raw packets securely in authorized storage. Do not upload sensitive source excerpts to public issue trackers.

## Explicit limits and safeguards

- No server-side approval, no signature validation, no verification of claimed officer identities or authorization at import time, and no promise of factual legal correctness.
- The browser reads selected files only after an explicit file-picker action, imposes file/count/row limits, renders content as text, and never sends the contents to any API or provider.
- A reported consensus score is a self-declared human judgment; without authenticated reviewer sign-off it cannot be called validated client acceptance.
- The summary JSON returns human_accuracy_percentage=null, client_acceptance_certified=false, identities_verified=false and packet_authenticity_cryptographically_verified=false.
- Only genuine, representative, independently reviewed answers should be used for management benchmarking. The synthetic 16-case diagnostic corpus is not part of the human-scored denominator.
- No Supabase changes, client production updates, paid AI requests, automatic legal determinations, or source takedowns.

## QA gates

- Node tests for CSV parsing, packet matching, two distinct reviewers, N/A exclusions, disagreement, adjudication, duplicate reviewers, forged/missing packets and minimized summary.
- Playwright test for three local files, per-dimension numerator/denominator, download, no API write and a missing-packet failure.
- Existing frontend build, full backend QA, PostgreSQL security, offline contract, monotonic build version and exact-commit Render staging deployment.

## Acceptance still open

Real AI answer-quality acceptance requires 20-30 distinct, representative genuine question-answer-authorized evidence sets and independent, authenticated reviewers. Operational casework approval and legal PDF currentness are separate human gates. This v148.7 batch implements the consolidation workflow, not completion of those acceptances.
