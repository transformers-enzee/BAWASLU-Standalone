# Canonical identity integration and staging audit — 28 October 2026

## Stable identity contract
- **Social Listening source post:** `social:<social_listening_results.id>`. This is the stored source row primary key and is independent of a sometimes-missing `provider_result_id`.
- **Smart Radar pilot post:** `radar:<pilot_smart_radar.source_posts.pilot_post_id>`. This is a different namespace; never map it to a Social Listening row using post text, name or an unverified URL.
- **Normalized candidate:** `candidate:<watchlist_items.id>`, for registry rows whose type is Candidate. Aliases are search labels, not new identities.
- **Promoted Intelligence:** `intelligence_items.source_id` now receives the canonical Social Listening ID on new promotions. `social_listening_results.promoted_intelligence_id` remains the authoritative existing foreign-key relationship. All old API `id` values remain unchanged.

## Measured Render Postgres field completeness
Read-only queries on Render Postgres `bawaslu-postgres`, 28 October 2026:

| Scope | Rows | Missing URL | Platform | Published time | Text content | Account | Provider/source ID |
|---|---:|---:|---:|---:|---:|---:|---:|
| Social Listening | 154 | 1 | 0 | 104 | 9 | 1 | 104 missing provider IDs |
| Intelligence | 7 | 1 | 0 | not yet separately checked | 0 | not yet separately checked | 7 missing source IDs |
| Promoted Social → Intelligence FK | 3 | — | — | — | — | — | 0 broken FK; 3 missing canonical IDs |

2 candidate profiles are registered. These are field-availability counts, **not** platform verification or evidence accuracy assertions.

**Important database mismatch:** `pilot_smart_radar.source_posts` is absent in this connected Render Postgres database (SQLSTATE 42P01). Smart Radar may be using another database, an unprovisioned schema, or a different environment. Verify its configured DATABASE_URL and applied migrations before attempting to reconcile the pilot source posts. Do not infer source IDs across the two systems.

## Safe next actions
1. Inspect the deployed database configuration and locate the real pilot schema. Do not display or copy credentials.
2. Run `cd backend && python -m scripts.backfill_source_ids` for dry-run of the 3 explicit promotions. Apply only after reviewing the zero-conflict report, using `--apply`; the script never overwrites populated IDs.
3. Validate that new promotions retain `social:<id>` through Social Listening → Inbox → Assistant.
4. Resolve the 104 missing publication timestamps and provider IDs through a provenance review. Do not populate timestamps based on collection time or invent provider identifiers.
5. Verify app role/session behavior and end-to-end staging QA before checking off the original Wednesday checklist items 6–10.

## QA status
Added `backend/tests/test_source_ids.py` and included it in the architecture branch's automated workflow. Source-level implementation pushed. The full build and deployment verification must be recorded separately.

## Verified pilot database location — follow-up, 28 October 2026
- The BAWASLU Supabase project (`bsekqkhgyjedcmptjnag`) contains `pilot_smart_radar.source_posts` and the other pilot review/QA tables. The Render-managed `bawaslu-postgres` connection is a separate database and must **not** be treated as the Smart Radar pilot store.
- Read-only Supabase verification of `RADAR-PHASE3-BATCH-001`: **109 source posts**, **109 distinct pilot post IDs**, and **zero missing** source URLs, platforms, publication timestamps, original content, or account fields.
- The prior missing-table error was a connection-to-the-wrong-database observation, not evidence that the pilot dataset was lost. Deployment must keep the Smart Radar pilot connection configured correctly. Avoid copying Supabase credentials into front-end code or documentation.
- Social Listening/Intelligence staging data still has the separately measured gaps above. The two stores remain separate namespaces and must not be joined on guessed text, people, or numeric IDs.

## Integration readiness — next live development batch
- Added authenticated `GET /api/integration/readiness` for **active nationwide National Administrator** only. It reports aggregate Social Listening provenance gaps, promoted FK/canonical-ID coverage and candidate totals from the app database. No source content or credentials leave this API.
- Cross-module audit found 3 existing promotions with explicit foreign keys, zero conflicts, and 3 eligible missing canonical IDs. `scripts.backfill_source_ids` remains dry-run by default; historical data was not changed by this sprint.
- Non-news Social Listening records account for the bulk of missing provider IDs and publication times. Missing publication times must not be replaced by collection times. Source capture remediation should be handled in the existing provider ingestion pipeline after field-level verification.
- Added `backend/tests/test_integration_readiness.py` for Viewer and regional-role denial and aggregate-only output. Included it in the architecture-branch CI workflow.
- The latest Render deployment is automatically triggered by branch pushes; check the newest deploy status before claiming the endpoint is live.

## Historical source ID repair control (new)
The authenticated nationwide National Administrator API now supports:
- `GET /api/integration/source-id-backfill/preview`: read-only counts for explicit promoted result IDs, missing IDs and conflicts.
- `POST /api/integration/source-id-backfill/apply`: request JSON `{"confirm":true,"expected_missing":<preview eligible_missing_ids>}`. Rejects no confirmation, role mismatch, conflicts or changed counts. Only writes empty `intelligence_items.source_id` values based on existing promoted foreign keys; original source evidence is not touched.
- No automatic backfill is run on deployment. Inspect and verify preview first. Prefer a non-production session for any smoke test of write endpoints.
- Manual sign-off is still needed for final controlled historical backfill and role/browser UAT.

## Release readiness gate — 28 October follow-up
- The administrator-only `GET /api/integration/readiness` now includes fail-closed `release_gates` for complete Social Listening source provenance, zero broken/missing/conflicting promoted canonical IDs, and required manual review. The separate Supabase pilot is explicitly excluded from these app-database gates.
- Existing 3 historical promoted records are still awaiting an authorized, confirmed backfill. This change does not run any write or provider request.
- Browser role UAT and a real-record end-to-end pass are still required before full checklist closure; the readiness endpoint never claims they were completed.
