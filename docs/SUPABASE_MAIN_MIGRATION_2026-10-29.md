# BAWASLU main database: Supabase (one-time legacy data migration)

The live Standalone application stays on Supabase (`DATABASE_URL`); do not switch it to Render PostgreSQL and do not seed duplicate source records.

Verified before migration:
- Supabase `public`: 2 app users, 0 Intelligence rows, 0 Social Listening results, 0 runs; pilot Smart Radar has 109 posts in its separate `pilot_smart_radar` schema.
- Legacy Render PostgreSQL (`bawaslu`): 7 Intelligence rows, 11 Social Listening runs, 154 results, 2 Watchlist rows, 0 Social Listening rules. All 11 runs have blank `rule_id` relationships.
- The four target tables have matching source/target column sets and the same IDs can be retained.

## Run safely

1. Keep Supabase `DATABASE_URL` as the existing app connection. Set `LEGACY_RENDER_DATABASE_URL` **privately** to the Render PostgreSQL internal URL for the `bawaslu` database. Never paste either credential into a chat, GitHub issue, frontend or logs.
2. Use a secured operator environment that can access both databases. Create backups/snapshots before any write. Run `cd backend && python -m scripts.migrate_legacy_to_supabase` to validate identities, identical columns, expected counts and an empty target.
3. Once the preview is confirmed, run `cd backend && python -m scripts.migrate_legacy_to_supabase --apply`. The script inserts the four related tables in order into a single target transaction and aborts without committing if counts or relationships differ.
4. Verify in Supabase: `SELECT COUNT(*) FROM public.social_listening_results;` should return **154**, `public.intelligence_items` **7**, `public.social_listening_runs` **11**, `public.watchlist_items` **2**. The existing 2 users and their access grants/sessions must remain intact.
5. Refresh `/administration/integration` while signed in as National Administrator. The historical canonical ID backfill is a separate explicit operation, not part of the migration.
6. Rotate the Supabase database credential previously shared in conversation and update Render environment settings.

**Not run yet.** The available Render DB connector can read the legacy records but cannot export credentials or execute writes; direct cross-connector record transfer was blocked. The source connection must be supplied through a private operator environment.
