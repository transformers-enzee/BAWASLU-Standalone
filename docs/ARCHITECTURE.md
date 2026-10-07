# GovIntel Standalone Architecture

## Platform boundary

GovIntel is the first tenant/product on a reusable intelligence platform core. Product-specific taxonomy, client export, prompts, and dashboard semantics remain configurable so BizIntel and BAWASLU can migrate later without copying the platform.

## Core domains

1. Evidence — immutable source/provenance and captured content.
2. Review — versioned AI/human decisions with one authoritative final state.
3. Story intelligence — relationship decisions and story clusters.
4. Findings — evidence-linked analyst drafts, distinct from raw evidence.
5. Media reference — canonical source plus versioned reach/impression/PRV/AVE metrics.
6. Export — product-specific client transformation; internal audit fields remain internal.
7. Audit — who/what changed each governed object.

## State model

- `pending`: no final review decision.
- `ai_reviewed`: AI decision passed deterministic validation and threshold.
- `human_required`: AI ambiguity or validation failure.
- `human_reviewed`: analyst decision is authoritative.
- `rejected`: record removed from downstream intelligence for a governed reason.

Test fixtures are orthogonal (`is_test_fixture=true`) and excluded from operational counts/exports.

## Production roadmap

- PostgreSQL + migrations.
- SSO/RBAC and tenant isolation.
- Object storage for raw captures/documents.
- Job queue for ingestion/AI processing.
- Model gateway with observability, rate controls, retry/idempotency.
- Story clustering with human-confirmable membership.
- Media-source alias management and reference import UI.
- Template-faithful client workbook generation and scheduled delivery.

## AI review pipeline (v0.2)

1. Provider returns a schema-constrained draft.
2. Deterministic validator checks allowed relevance/sentiment, approved KPM taxonomy and verbatim excerpt.
3. Routing policy evaluates multiple confidence dimensions and evidence completeness.
4. Safe high-confidence cases may enter `ai_reviewed` when auto-apply is explicitly enabled.
5. All other cases enter `human_required` with an explicit exception reason.
6. Human review is authoritative and AI never overwrites it.
7. Every AI/human decision is appended to `review_decisions`; evidence stores only the current authoritative state.

## Regression benchmark

Benchmark runs are non-mutating. They compare AI predictions against the analyst-reviewed pilot and store results separately. Historical metadata-only rows are labelled so they cannot be mistaken for content-complete evaluation examples.

## Shared application shell (v0.8)

The browser shell is product-aware. It sends `X-Product-ID` on API requests and changes navigation according to the selected product. Product switching does not merge data: every shared Evidence query and derived scope remains tenant/product constrained.

GovIntel is the only product with an enabled operational review adapter in v0.8. BizIntel and BAWASLU are deliberately read-only at the shared Evidence layer until their specialist workflows have been migrated and regression-tested. This prevents GovIntel's KPM taxonomy/review rules from being accidentally applied to another product.

## Online media reference snapshot (v0.8)

The current GovIntel Online News media reference is a versioned snapshot effective 2026-09-28. Current lookup uses active sources with an open metric version. Superseded KDN/KOMPILASI values are closed with `effective_to` rather than deleted, preserving audit history. Source aliases are scoped by tenant and product.
