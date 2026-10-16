"""PostgreSQL-only concurrency validation; requires isolated TEST_DATABASE_URL.
No AI or SocialCrawl requests are made. Never point at a production database.
Run manually in an isolated test environment with pytest -m postgres_concurrency.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import AIBudgetReservation
from app.db import Base
from app.auto_relevance import reserve_automatic_ai_request

pytestmark=pytest.mark.postgres_concurrency

def test_concurrent_request_reservations_are_bounded(monkeypatch):
    url=os.getenv('BAWASLU_TEST_DATABASE_URL','')
    if os.getenv('BAWASLU_ALLOW_ISOLATED_DB_TEST','')!='YES' or not url or 'postgres' not in url:
        pytest.skip('Isolated BAWASLU_TEST_DATABASE_URL required')
    if any(x in url.lower() for x in ('prod','render.com','supabase.co')):
        pytest.skip('Refusing potentially production-hosted database')
    engine=create_engine(url)
    if engine.dialect.name!='postgresql':
        pytest.skip('PostgreSQL required')
    # Unique isolated schema; never drop a preexisting schema or table.
    with engine.begin() as conn:
        schema='bawaslu_budget_qa_'+uuid.uuid4().hex[:12]
        conn.execute(text(f'CREATE SCHEMA {schema}'))
        conn.execute(text(f'CREATE TABLE {schema}.ai_budget_reservations (id SERIAL PRIMARY KEY, campaign_id INTEGER NOT NULL, budget_period VARCHAR(24) NOT NULL, reserved_requests INTEGER NOT NULL DEFAULT 0, UNIQUE(campaign_id,budget_period))'))
    # Each worker has its own connection and session. Schema is selected with search_path.
    Session=sessionmaker(bind=engine,autoflush=False)
    monkeypatch.setenv('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN','3')
    monkeypatch.setenv('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN','4')
    def worker(_):
        db=Session()
        try:
            db.execute(text(f'SET search_path TO {schema}, public'))
            db.commit()
            return reserve_automatic_ai_request(db,999999)
        finally:
            db.close()
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes=list(pool.map(worker,range(12)))
        assert sum(outcomes)==3
        with engine.connect() as conn:
            rows=conn.execute(text(f"SELECT budget_period,reserved_requests FROM {schema}.ai_budget_reservations WHERE campaign_id=999999")).all()
            assert len(rows)==2
            assert sorted(row[1] for row in rows)==[3,3]
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS {schema} CASCADE'))
        engine.dispose()
