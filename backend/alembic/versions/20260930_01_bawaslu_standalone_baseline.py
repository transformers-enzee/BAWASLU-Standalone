"""BAWASLU standalone v0.1 baseline

Revision ID: 20260930_01
Revises:
Create Date: 2026-09-30
"""
from alembic import op
from app.db import Base
from app import models  # noqa: F401
revision='20260930_01'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
