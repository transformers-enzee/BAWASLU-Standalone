"""Canonical source-ID backfill tests with isolated SQLite tables; no staging writes."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from scripts.backfill_source_ids import run

@pytest.fixture
def session():
    engine=create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE social_listening_results (id INTEGER PRIMARY KEY, promoted_intelligence_id INTEGER)"))
        conn.execute(text("CREATE TABLE intelligence_items (id INTEGER PRIMARY KEY, source_id TEXT)"))
        conn.execute(text("INSERT INTO intelligence_items VALUES (11,''),(12,'legacy:keep')"))
        conn.execute(text("INSERT INTO social_listening_results VALUES (5,11),(6,12)"))
    with Session(engine) as sess:
        yield sess
    engine.dispose()

def test_dry_run_never_updates(session):
    report=run(session,apply=False)
    assert report["linked"]==2
    assert report["eligible_missing_ids"]==1
    assert report["conflicting_nonblank_ids"]==1
    assert session.execute(text("SELECT source_id FROM intelligence_items WHERE id=11")).scalar()==""

def test_conflict_blocks_entire_apply(session):
    with pytest.raises(RuntimeError,match="Conflicting"):
        run(session,apply=True)
    assert session.execute(text("SELECT source_id FROM intelligence_items WHERE id=11")).scalar()==""

def test_apply_preserves_populated_ids(session):
    session.execute(text("UPDATE intelligence_items SET source_id='social:6' WHERE id=12"))
    session.commit()
    report=run(session,apply=True)
    assert report["updated"]==1
    assert report["already_correct"]==1
    assert session.execute(text("SELECT source_id FROM intelligence_items WHERE id=11")).scalar()=="social:5"
    assert session.execute(text("SELECT source_id FROM intelligence_items WHERE id=12")).scalar()=="social:6"
    assert run(session,apply=True)["updated"]==0
