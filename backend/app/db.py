import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./bawaslu.db')
# Render's managed Postgres connection string is usually postgresql://...
# This project installs psycopg v3, so normalize the scheme explicitly.
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL[len('postgresql://'):]

if DATABASE_URL.startswith('postgresql'):
    parsed = make_url(DATABASE_URL)
    if parsed.host and parsed.host.endswith('.pooler.supabase.com') and parsed.port == 5432:
        DATABASE_URL = parsed.set(port=6543).render_as_string(hide_password=False)
connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
if DATABASE_URL.startswith('postgresql'):
    connect_args['prepare_threshold'] = None
engine_kwargs = {'future': True, 'connect_args': connect_args}
if not DATABASE_URL.startswith('sqlite'):
    # Bound connections against the shared Supabase session pool.
    engine_kwargs.update(pool_size=2, max_overflow=0, pool_timeout=8,
                         pool_recycle=120, pool_pre_ping=True)
    connect_args['options'] = '-c idle_in_transaction_session_timeout=60000'
if DATABASE_URL in ('sqlite:///:memory:', 'sqlite://'):
    engine_kwargs['poolclass'] = StaticPool
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
