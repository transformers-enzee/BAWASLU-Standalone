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
    op.add_column('evidence_assessments',sa.Column('sentiment_confidence',
        sa.String(length=32),nullable=False,server_default=''))
    op.add_column('evidence_assessments',sa.Column('sentiment_explanation',
        sa.Text(),nullable=False,server_default=''))
    op.add_column('evidence_assessments',sa.Column('sentiment_model',
        sa.String(length=100),nullable=False,server_default=''))

def downgrade():
    op.drop_column('evidence_assessments','sentiment_model')
    op.drop_column('evidence_assessments','sentiment_explanation')
    op.drop_column('evidence_assessments','sentiment_confidence')
