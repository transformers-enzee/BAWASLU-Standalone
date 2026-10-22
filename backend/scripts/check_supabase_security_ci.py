"""Ephemeral Postgres integration test: Supabase-like anon/authenticated roles.

Requires SECURITY_TEST_DSN pointing ONLY at bawaslu_security_ci. No production
connection strings or API keys are accepted. Runs from GitHub Actions.
"""
import os
from pathlib import Path
import psycopg

TABLES = [
  "access_grants",
  "alembic_version",
  "audit_events",
  "data_sources",
  "entity_relationships",
  "evidence_files",
  "external_data_connectors",
  "intelligence_items",
  "intelligence_sequences",
  "issue_categories",
  "migration_batches",
  "migration_staging_records",
  "session_tokens",
  "social_listening_provider_usage",
  "social_listening_results",
  "social_listening_rules",
  "social_listening_runs",
  "source_accounts",
  "triage_generations",
  "users",
  "watchlist_items",
  "monitoring_campaigns",
  "campaign_runs",
  "campaign_evidence",
  "evidence_assessments",
  "evidence_reviews",
  "issue_category_phrases"
]
SQL_FILE = Path(__file__).resolve().parents[1] / "security" / "64_1_supabase_security_ci_only.sql"

def main():
    dsn = os.getenv("SECURITY_TEST_DSN", "")
    if not dsn or "bawaslu_security_ci" not in dsn:
        raise RuntimeError("Only the ephemeral bawaslu_security_ci database is supported")
    with psycopg.connect(dsn, autocommit=True) as conn:
        db, role = conn.execute("SELECT current_database(), current_user").fetchone()
        if db != "bawaslu_security_ci" or role != "postgres":
            raise RuntimeError("Refusing to run outside expected CI database and role")
        for role_name in ("anon", "authenticated"):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,)).fetchone():
                conn.execute(f"CREATE ROLE {role_name} NOLOGIN")
        names = {row[0] for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
        missing = set(TABLES) - names
        if missing:
            raise RuntimeError("Alembic schema missing: " + ", ".join(sorted(missing)))
        table_names = ", ".join("public." + name for name in TABLES)
        conn.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table_names} TO anon, authenticated")
        for role_name in ("anon", "authenticated"):
            assert conn.execute("SELECT has_table_privilege(%s,'public.users','SELECT')", (role_name,)).fetchone()[0], "Expected simulated insecure starting privileges"

        script = SQL_FILE.read_text()
        # Security guard must reject accidental invocation, with no change.
        try:
            conn.execute(script)
        except psycopg.errors.RaiseException:
            conn.execute("ROLLBACK")
        else:
            raise AssertionError("The staging guard must block application without explicit ephemeral setup")
        assert conn.execute("SELECT has_table_privilege('anon','public.users','SELECT')").fetchone()[0]
        conn.execute("SET bawaslu.stage_approved TO 'yes'")
        conn.execute("SET bawaslu.stage_name TO 'CI_EPHEMERAL'")
        conn.execute(script)
        for table in TABLES:
            assert conn.execute(
                "SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(%s)",
                ("public." + table,)
            ).fetchone()[0], f"RLS not enabled on {table}"
            for role_name in ("anon", "authenticated"):
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                    assert not conn.execute(
                        "SELECT has_table_privilege(%s,%s,%s)",
                        (role_name, "public." + table, privilege)
                    ).fetchone()[0], f"{role_name} retains {privilege} on {table}"
        # App-owned PostgreSQL connection must still be able to write normally.
        cid = conn.execute(
            "INSERT INTO public.issue_categories(name,active,sort_order) VALUES (%s,%s,%s) RETURNING id",
            ("CI security smoke check", True, 9999)
        ).fetchone()[0]
        assert cid > 0
        conn.execute("SET ROLE anon")
        try:
            try:
                conn.execute("SELECT id FROM public.users LIMIT 1")
            except psycopg.errors.InsufficientPrivilege:
                pass
            else:
                raise AssertionError("anon role must be denied direct user-table access")
        finally:
            conn.execute("RESET ROLE")
        print(f"PASS: {len(TABLES)} application tables secured, API roles denied, app DB role preserved")

if __name__ == "__main__":
    main()
