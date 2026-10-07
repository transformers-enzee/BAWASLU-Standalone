# Shared platform compatibility — GovIntel / BizIntel / BAWASLU

v0.4 keeps GovIntel as the first production implementation while reserving explicit platform boundaries for the two migration references supplied by NK Workspace.

## Shared core candidates

- Authentication, users, tenant boundary and RBAC.
- Evidence/raw-source storage and immutable provenance.
- AI review execution, structured validation and human exception routing.
- Relationship proposals/decisions and audit history.
- Source/provider identity and canonicalisation.
- Findings/derived intelligence with evidence links.
- Versioned configuration and export framework.

## Product-specific modules that must not be flattened

**GovIntel:** KPM taxonomy, media reference metrics, client TOPIK/story label, KPM workbook export, media-monitoring review states.

**BizIntel:** tenant/source-provider ingestion, field mappings, raw source records, coverage metadata/items, relationship engine versions, gold labels/datasets, calibration, shadow review and independent second review.

**BAWASLU:** intelligence items/sequences, source accounts and identity resolution, issue categories, actors/entity relationships, watchlists, jurisdiction/geography and mismatch rules, triage generations/approval, evidence files, access grants and audit events.

## Boundary rule

Every shared-core record that can contain customer/product data must carry a tenant/product scope before BizIntel or BAWASLU data is migrated. GovIntel currently has `tenant_id` on evidence and users; v0.4 treats that as a migration seam, not yet as complete row-level tenant isolation across every table.

## Migration principle

Do not port Base44 UI/database mechanics verbatim. Preserve contracts, state transitions, provenance and validated business rules; reimplement them on the standalone core with migration tests and product-specific adapters.

## v0.5 implementation

The shared core now has first-class `Tenant`, `Product`, `TenantProduct`, and `UserProductAccess` records. `Evidence` carries both `tenant_id` and `product_id`, plus neutral shared-contract fields (`evidence_type`, `source_provider`, `external_id`, raw metadata, provenance). The three registered products are `govintel`, `bizintel`, and `bawaslu`.

The API resolves product context from `X-Product-ID`; authenticated users are denied cross-product access unless explicitly granted. Evidence list/detail/review/AI-exception paths apply tenant+product filtering, and scoped lookup returns 404 rather than revealing a record in another scope.

This is the foundation, not a claim that BizIntel or BAWASLU have been migrated. Their specialist entities remain product adapters to be implemented in later versions. Before either product is exposed to users, every relationship/finding/export route must also be converted to explicit scope-aware queries and covered by integration tests.

## v0.6 implementation

Derived operational data is now scope-aware: relationships/proposals, story clusters, findings, benchmark runs, media-source reference data, command-centre counts and exports are resolved within an explicit tenant/product context. Cross-scope relationship and finding creation validates every referenced Evidence row before writing. The GovIntel KPM workbook is now an explicit GovIntel adapter export rather than a platform-global export.

`app/product_adapters.py` defines the first product contracts for GovIntel, BizIntel and BAWASLU. `migration_manifests/` records which legacy entities map to the neutral Evidence envelope and which specialist entities must remain product-owned. These manifests are migration contracts only; no BizIntel or BAWASLU operational data is imported in v0.6.

## v0.7 implementation

Legacy migration is staging-first. Migration batches preserve the original payload, validate mappings before commit, and route product-owned semantics into `SpecialistRecord` rather than forcing them into shared Evidence. BizIntel and BAWASLU remain unimported by default.

## v0.8 implementation

The frontend is now a shared NK Intelligence shell with an explicit product selector. `X-Product-ID` drives tenant/product scope for the API. GovIntel exposes its mature operational workflows; BizIntel and BAWASLU expose only shared Evidence and migration status until their specialist review adapters are implemented. GovIntel-specific review and AI endpoints reject non-GovIntel product scopes.

Media-source aliases now carry tenant/product scope, closing the remaining alias-resolution leakage risk. GovIntel's current Online media-reference snapshot is versioned separately from historical provisional KDN/KOMPILASI values.
