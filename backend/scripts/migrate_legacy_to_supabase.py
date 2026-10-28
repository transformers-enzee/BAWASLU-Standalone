"""One-time migration: Render legacy BAWASLU rows -> existing Supabase application DB.

Dry-run by default. Never copies users, access grants, sessions or pilot Smart Radar.
Requires two private server-side URLs: LEGACY_RENDER_DATABASE_URL and DATABASE_URL.
Run from backend: python -m scripts.migrate_legacy_to_supabase [--apply]
"""
import argparse
import os
from sqlalchemy import create_engine, MetaData, Table, select, func, text

TABLES = ("intelligence_items", "social_listening_runs", "watchlist_items", "social_listening_results")
EXPECTED = {"intelligence_items": 7, "social_listening_runs": 11,
            "watchlist_items": 2, "social_listening_results": 154}

def url(name):
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Missing private environment variable {name}")
    if value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    if not value.startswith(("postgresql+psycopg://", "postgresql+psycopg2://")):
        raise RuntimeError(f"{name} must use PostgreSQL")
    return value

def migrate(apply=False):
    source = create_engine(url("LEGACY_RENDER_DATABASE_URL"), future=True)
    target = create_engine(url("DATABASE_URL"), future=True)
    try:
        with source.connect() as src, target.connect() as dst:
            origin = src.execute(text("SELECT current_database()")).scalar_one()
            destination = dst.execute(text("SELECT current_database()")).scalar_one()
            if origin != "bawaslu" or destination != "postgres":
                raise RuntimeError("Unexpected source/target database identity; migration stopped")
            tables = {}
            for name in TABLES:
                source_table = Table(name, MetaData(), autoload_with=src)
                target_table = Table(name, MetaData(), autoload_with=dst)
                source_cols = {c.name for c in source_table.columns}
                target_cols = {c.name for c in target_table.columns}
                if source_cols != target_cols:
                    raise RuntimeError(f"Schema mismatch: {name}")
                count = src.execute(select(func.count()).select_from(source_table)).scalar_one()
                existing = dst.execute(select(func.count()).select_from(target_table)).scalar_one()
                if count != EXPECTED[name] or existing != 0:
                    raise RuntimeError(f"{name}: expected {EXPECTED[name]} source and 0 destination rows; got {count} and {existing}")
                tables[name] = (source_table, target_table)
            if not apply:
                return {"mode": "dry_run", "source": origin, "target": destination,
                        "planned": EXPECTED, "users_preserved": True}
        # All target writes happen in one transaction, after the same preconditions
        # are rechecked under locks on the destination tables.
        with source.connect() as src, target.begin() as dst:
            dst.execute(text("LOCK TABLE " + ", ".join("public." + n for n in TABLES) + " IN SHARE ROW EXCLUSIVE MODE"))
            counts = {}
            for name in TABLES:
                src_table, dst_table = tables[name]
                if dst.execute(select(func.count()).select_from(dst_table)).scalar_one() != 0:
                    raise RuntimeError(f"{name} acquired rows during preflight")
                rows = [dict(row) for row in src.execute(select(src_table)).mappings()]
                if len(rows) != EXPECTED[name]:
                    raise RuntimeError(f"{name} changed at source since preview")
                if rows:
                    dst.execute(dst_table.insert(), rows)
                counts[name] = len(rows)
                # Sequence must advance past preserved legacy primary keys.
                dst.execute(text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), "
                                 "GREATEST((SELECT MAX(id) FROM public." + name + "), 1), true)"),
                            {"tbl": "public." + name})
            linked = dst.execute(text("""SELECT COUNT(*) FROM public.social_listening_results s
                       JOIN public.intelligence_items i ON i.id=s.promoted_intelligence_id
                       WHERE s.promoted_intelligence_id IS NOT NULL""")).scalar_one()
            broken = dst.execute(text("""SELECT COUNT(*) FROM public.social_listening_results s
                       LEFT JOIN public.social_listening_runs r ON r.id=s.run_id WHERE r.id IS NULL""")).scalar_one()
            if linked != 3 or broken:
                raise RuntimeError("Relationship verification failed; rolling back")
        return {"mode": "applied", "source": origin, "target": destination,
                "imported": counts, "linked": linked, "users_preserved": True}
    finally:
        source.dispose()
        target.dispose()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit verified import; default is read-only preview")
    args = parser.parse_args()
    import json
    print(json.dumps(migrate(args.apply), indent=2))
