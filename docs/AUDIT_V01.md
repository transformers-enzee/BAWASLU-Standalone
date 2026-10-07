# Source Audit Summary — BAWASLU → NK Intelligence

Audited sources:

- `bawaslu-insight-core.zip`
- `GovIntel-Standalone-v0.27.zip`

The BAWASLU source contains 13 Base44 entities and specialist workflows covering jurisdiction, geographic access, source identity/provenance, watchlists, actor relationships, evidence files, V3 triage provenance, duplicates, human validation and audit.

GovIntel v0.27 provides the target standalone pattern: FastAPI/SQLAlchemy, explicit migrations, testable server-side scope enforcement, provider abstraction, migration staging and deployment packaging. Its existing BAWASLU migration manifest is useful as a shared-platform reference but is insufficient as a final BAWASLU schema because several specialist entities were mapped to generic `SpecialistRecord` JSON and `IssueCategory`, `DataSource`, and `ExternalDataConnector` were not included.

v0.1 therefore uses shared NK architectural conventions while implementing BAWASLU specialist concepts as first-class tables. The legacy Base44 source is retained in the release package for direct parity comparison during later migration testing.
