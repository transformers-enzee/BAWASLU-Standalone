import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./bawaslu.db')
# Render's managed Postgres connection string is usually postgresql://...
# This project installs psycopg v3, so normalize the scheme explicitly.
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL[len('postgresql://'):]

connect_args = {'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}
engine_kwargs = {'future': True, 'connect_args': connect_args}
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
