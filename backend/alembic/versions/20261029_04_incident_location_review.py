"""Officer-verified source jurisdiction, isolated from account profile geography.

Revision ID: 20261029_04
Revises: 20261029_03
"""
from alembic import op
import sqlalchemy as sa
revision='20261029_04'
down_revision='20261029_03'
branch_labels=None
depends_on=None

def upgrade():
    if 'campaign_jurisdiction_reviews' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table('campaign_jurisdiction_reviews',
        sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
        sa.Column('result_id',sa.Integer(),sa.ForeignKey('social_listening_results.id'),nullable=False),
        sa.Column('province',sa.String(length=128),nullable=False,server_default=''),
        sa.Column('evidence_fingerprint',sa.String(length=64),nullable=False,server_default=''),
        sa.Column('decision',sa.String(length=24),nullable=False,server_default='UNVERIFIED'),
        sa.Column('rationale',sa.Text(),nullable=False,server_default=''),
        sa.Column('reviewer_id',sa.String(length=128),nullable=False,server_default=''),
        sa.Column('reviewed_at',sa.DateTime(),nullable=True),
        sa.UniqueConstraint('campaign_id','result_id',name='uq_campaign_incident_location'))
    op.create_index('ix_campaign_jurisdiction_reviews_campaign_id',
        'campaign_jurisdiction_reviews',['campaign_id'])
    op.create_index('ix_campaign_jurisdiction_reviews_result_id',
        'campaign_jurisdiction_reviews',['result_id'])
    if op.get_bind().dialect.name=='postgresql':
        op.execute('ALTER TABLE campaign_jurisdiction_reviews ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE campaign_jurisdiction_reviews FROM anon, authenticated')

def downgrade():
    op.drop_index('ix_campaign_jurisdiction_reviews_result_id',
                  table_name='campaign_jurisdiction_reviews')
    op.drop_index('ix_campaign_jurisdiction_reviews_campaign_id',
                  table_name='campaign_jurisdiction_reviews')
    op.drop_table('campaign_jurisdiction_reviews')
