# BAWASLU SmartRadar v185.9 — Human Gate 1 integrity and QA readiness

Staging development: architecture-v2-foundation-20261015.
Architecture: raw Social Listening evidence -> information QA -> proposed insights -> independent insight publication approval. Human Gate 3 remains offline/validated model-learning governance, not automatic retraining.

## Bulk release scope
1. Review decisions capture source-content/provenance SHA-256 digest, latest assessment ID, and latest officer sentiment correction ID. A decision is **REVALIDATION_REQUIRED** after a changed saved source, assessment or sentiment revision, even when the selected status was previously OFFICER_VERIFIED. Existing decisions from v185.8 without source digest are revalidation-required rather than silently trusted.
2. Field corrections and restore actions require a fresh source digest, the latest assessment ID, and a field-specific optimistic revision. Source is reloaded under a database row lock and geographic scope rechecked before write. Stale or out-of-scope requests fail closed (409 or 404); original provider text/payload and historical assessments are not modified.
3. An officer cannot mark unassessed/pending AI output as OFFICER_VERIFIED. A completed saved assessment and original source trace are required. OFFICER_VERIFIED means **information QA reviewed**, not verified allegations, legal findings, official insights or automatic Command Centre publication.
4. The officer UI separately presents the last non-human AI relevance and current effective relevance with basis (AI vs officer correction). It no longer labels a human override as if it were an AI classification.
5. The paginated officer queue now filters both assessment category and information QA status, including Needs Review, Information Reviewed, Held, Excluded and Revalidation Required, with cursor pagination and all existing geographic and campaign access checks.
6. Display QA counts across **currently loaded authorized records** only. These must not be described as a whole-campaign count, AI accuracy percentage, legal-violation rate, or statistically representative sample.
7. An officer can restore the original saved AI sentiment as a new audited revision; all restoration operations remain append-only and require a reason.
8. No Supabase schema changes, migrations, paid provider calls, direct client database credentials, automatic AI learning or unapproved insight publication.

## Feature flags (initial deployment)
- `BAWASLU_INBOX_GATE1_READ_ENABLED=true` (existing staged read lane)
- `BAWASLU_INBOX_GATE1_WRITE_ENABLED=false` (**do not change as part of deployment**)
- `BAWASLU_INBOX_GATE1_PILOT_MODE` and `BAWASLU_INBOX_GATE1_PILOT_CAMPAIGN_IDS` are only for a later, explicitly authorized write pilot.

## Automated quality gates
- Source digest and stale evidence/assessment token rejection, including review decisions and sentiment correction writes.
- Source-scope and campaign authorization, versioned history, append-only restoration, no original source modification.
- Status triage integration via in-memory SQLAlchemy database; no access to actual officer data.
- Backend full pytest regression, frontend build/visual tests, Playwright, and GitHub Actions GHCR publication.

## Remaining manual pilot gate (not automated)
After this image is deployed read-only and smoke-tested, a designated officer/admin must authorize a disposable staging-only evidence test campaign before enabling writes. Validate with the exact source record and audit trail: correction with rationale -> stale request rejected -> historical value restored as a new version -> information review marked verified -> source/assessment change causes REVALIDATION_REQUIRED -> Command Centre unchanged. Disable write flag again on completion.

**Do not enable Gate 1 corrections on all campaigns or production, and do not proceed to Gate 2 publication from a Gate 1 review status alone.**
