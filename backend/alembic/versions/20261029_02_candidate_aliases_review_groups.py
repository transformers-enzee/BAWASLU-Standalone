"""Persist officer-approved candidate aliases and reviewable evidence groups.

Revision ID: 20261029_02
Revises: 20261029_01
"""
from alembic import op
import sqlalchemy as sa

revision='20261029_02'
down_revision='20261029_01'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    if 'candidate_aliases_json' not in {c['name'] for c in sa.inspect(bind).get_columns('watchlist_items')}:
        op.add_column('watchlist_items',sa.Column('candidate_aliases_json',sa.Text(),
            nullable=False,server_default='[]'))
    if 'campaign_finding_groups' in sa.inspect(bind).get_table_names():
        return
    op.create_table('campaign_finding_groups',
        sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),
                  nullable=False),
        sa.Column('group_key',sa.String(length=64),nullable=False),
        sa.Column('group_type',sa.String(length=40),nullable=False),
        sa.Column('label',sa.String(length=255),nullable=False,server_default=''),
        sa.Column('source_ids_json',sa.Text(),nullable=False,server_default='[]'),
        sa.Column('review_status',sa.String(length=32),nullable=False,server_default='PROPOSED'),
        sa.Column('review_rationale',sa.Text(),nullable=False,server_default=''),
        sa.Column('created_by',sa.String(length=128),nullable=False,server_default=''),
        sa.Column('reviewed_by',sa.String(length=128),nullable=False,server_default=''),
        sa.Column('created_at',sa.DateTime(),nullable=True),
        sa.Column('reviewed_at',sa.DateTime(),nullable=True),
    )
    op.create_index('ix_campaign_finding_groups_campaign_id','campaign_finding_groups',['campaign_id'])
    op.create_index('ix_campaign_finding_groups_group_key','campaign_finding_groups',['group_key'],unique=True)
    op.create_index('ix_campaign_finding_groups_group_type','campaign_finding_groups',['group_type'])
    op.create_index('ix_campaign_finding_groups_review_status','campaign_finding_groups',['review_status'])
    if op.get_bind().dialect.name=='postgresql':
        # Server-side SQLAlchemy access only. Never expose these records
        # directly to anonymous/authenticated Supabase Data API clients.
        op.execute('ALTER TABLE campaign_finding_groups ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE campaign_finding_groups FROM anon, authenticated')

def downgrade():
    for name in ('ix_campaign_finding_groups_review_status',
                 'ix_campaign_finding_groups_group_type',
                 'ix_campaign_finding_groups_group_key',
                 'ix_campaign_finding_groups_campaign_id'):
        op.drop_index(name,table_name='campaign_finding_groups')
    op.drop_table('campaign_finding_groups')
    op.drop_column('watchlist_items','candidate_aliases_json')
