"""Persist independent sentiment explanation and model provenance.

Revision ID: 20261029_01
Revises: 20261015_02
"""
from alembic import op
import sqlalchemy as sa

revision='20261029_01'
down_revision='20261015_02'
branch_labels=None
depends_on=None

def upgrade():
    existing={x['name'] for x in sa.inspect(op.get_bind()).get_columns('evidence_assessments')}
    if 'sentiment_confidence' not in existing:
        op.add_column('evidence_assessments',sa.Column('sentiment_confidence',
        sa.String(length=32),nullable=False,server_default=''))
    if 'sentiment_explanation' not in existing:
        op.add_column('evidence_assessments',sa.Column('sentiment_explanation',
        sa.Text(),nullable=False,server_default=''))
    if 'sentiment_model' not in existing:
        op.add_column('evidence_assessments',sa.Column('sentiment_model',
        sa.String(length=100),nullable=False,server_default=''))

def downgrade():
    # Columns may have existed before this migration on fresh bootstrap.
    # Never destroy them during a rollback of an already bootstrapped DB.
    pass
