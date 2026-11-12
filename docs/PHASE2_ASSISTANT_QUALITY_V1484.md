# BAWASLU Phase 2 — Assistant Answer-Quality Evaluation v148.4

**Release environment:** Staging only, branch architecture-v2-foundation-20261015.
**Scope:** Source-grounded Assistant chat, not classification/model fine-tuning.

## Rationale

v148.3 validated citation *identifiers*, PDF review status and contextual source cards, but did not provide reusable signals for a question's topical match, a two-module comparison's coverage, or conflicting sentiment labels for the same source. The new evaluator provides reproducible diagnostics without claiming to measure actual factual accuracy.

## Four checks

| Dimension | Automated evidence | Explicit limitation |
|---|---|---|
| Citation grounding | Visible source IDs are authorized and genuinely cited in the answer | Matching IDs are not proof of claim truth |
| Topical source relevance | Question-specific words appear in excerpts of cited sources | Keyword overlap is not semantic entailment; missing synonyms can trigger review |
| Legal uncertainty | A legal answer has cited an officer-reviewed legal PDF page, with legal currentness still unverified | Human PDF review does not establish effective law or amendments |
| Cross-module consistency | A cross-module comparison selects both formal Inbox and social evidence; duplicate social sources do not have conflicting sentiment | Completeness of types does not prove factual agreement |

Each status is PASS, REVIEW_REQUIRED or NOT_APPLICABLE. The returned metadata explicitly sets human_accuracy=null, human_gold_answers_evaluated=0, claim_truth_verified=false, legal_currentness_verified=false and semantic_entailment_verified=false. The UI never displays an aggregate percentage.

## 16-case synthetic diagnostic corpus

File: backend/tests/fixtures/assistant_answer_readiness_v1484.json

Cases cover: valid Gibran citation; structured but invisible Prabowo citation; off-topic Ganjar source for a Gibran question; fabricated Riau source ID; broad Indonesian sentiment question; comparison with both Riau modules; missing formal evidence; missing social evidence; unreviewed election-law PDF; officer-reviewed legal PDF without currentness; unreviewed PDF summary; social allegation substituted for legal authority; duplicate social source with conflicting sentiment; repeated consistent sentiment; Indonesian Pilkada/Riau matching; and no authorized evidence.

Every fixture has its expected result per dimension. The suite includes deliberate failure cases and forbids external calls. Passing all fixtures demonstrates only **software behavior on synthetic test cases**, not 100% model accuracy or BAWASLU sign-off.

## Existing Assistant UI

The reply adds a small expandable **Automated answer checks** section under source-citation integrity, with rule-based warnings. It does not add a new sidebar module or replace substantive human review.

No Supabase writes or migrations, no social crawling, no automatic legal determinations, no production push, and no paid model calls during these tests.

## Release gates

- Backend 16-case parameterized suite and extra safety checks.
- Frontend build contract and browser QA for warning labels and limitations.
- PostgreSQL-security, offline-contract and sequential-version checks.
- Exact v148.4 staging SHA live in Render before code release marked DONE.

## Human acceptance remains separate

To measure real answer quality, have qualified BAWASLU officers jointly review at least 20–30 distinct real *question/authorized evidence/model response* triples across public concerns, candidate narratives, violation signals, provincial jurisdiction, official platform policy, PDF procedure, cross-module comparisons and no-evidence requests. Freeze source snapshots and model outputs before review. Log reviewer ID/date, expected findings, source relevance, claim grounding, legal uncertainty, module consistency, evidence references, incorrect statements and adjudication. Calculate each dimension's numerator/denominator only **after** human ratings; record uncertain and N/A separately.

Current staging dependencies on 12 Nov 2026: one active PDF, zero officer-reviewed legal PDFs and no actual officer cases. These remain open acceptance items.
