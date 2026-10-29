"""Safe one-time issue screening vocabulary for newly unconfigured taxonomies.

Revision ID: 20261029_05
Revises: 20261029_04
"""
from alembic import op
from app.issue_phrase_seed import seed_default_issue_phrases
revision='20261029_05'
down_revision='20261029_04'
branch_labels=None
depends_on=None

def upgrade():
    seed_default_issue_phrases(op.get_bind())

def downgrade():
    # Seed rows may subsequently be edited or disabled by administrators.
    # Preserve their later decisions rather than deleting operational data.
    pass
