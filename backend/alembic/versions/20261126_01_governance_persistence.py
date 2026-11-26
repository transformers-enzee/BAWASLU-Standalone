"""Additive human review persistence (v184.5).

Revision ID: 20261126_01
Revises: 20261117_01
Not auto-applied on Render staging; enable APIs after scoped migration QA.
"""
from alembic import op
import sqlalchemy as sa
revision='20261126_01'
down_revision='20261117_01'
branch_labels=None
depends_on=None

def upgrade():
    tables=set(sa.inspect(op.get_bind()).get_table_names())
    if 'governance_field_corrections' not in tables:
        op.create_table('governance_field_corrections',
            sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
            sa.Column('result_id',sa.Integer(),sa.ForeignKey('social_listening_results.id'),nullable=False),
            sa.Column('field',sa.String(80),nullable=False),
            sa.Column('human_value',sa.String(300),nullable=False),
            sa.Column('reason',sa.Text(),nullable=False),
            sa.Column('reviewer_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
            sa.Column('revision',sa.Integer(),nullable=False),
            sa.Column('status',sa.String(24),nullable=False),
            sa.Column('created_at',sa.DateTime(),server_default=sa.text('CURRENT_TIMESTAMP'),nullable=False),
            sa.UniqueConstraint('campaign_id','result_id','field','revision',name='uq_governance_field_revision'))
        op.create_index('ix_governance_correction_campaign','governance_field_corrections',['campaign_id'])
        op.create_index('ix_governance_correction_result','governance_field_corrections',['result_id'])
    if 'governance_insights' not in tables:
        op.create_table('governance_insights',
            sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
            sa.Column('title',sa.String(255),nullable=False),
            sa.Column('evidence_ids_json',sa.Text(),nullable=False),
            sa.Column('analysis_scope',sa.String(180),nullable=False),
            sa.Column('source_digest',sa.String(64),nullable=False),
            sa.Column('claim_status',sa.String(24),nullable=False),
            sa.Column('evidence_verified',sa.Boolean(),server_default=sa.text('false'),nullable=False),
            sa.Column('contains_high_impact_claims',sa.Boolean(),server_default=sa.text('false'),nullable=False),
            sa.Column('high_impact_reviewed',sa.Boolean(),server_default=sa.text('false'),nullable=False),
            sa.Column('state',sa.String(32),nullable=False),
            sa.Column('revision',sa.Integer(),nullable=False),
            sa.Column('proposer_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
            sa.Column('approver_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=True),
            sa.Column('review_rationale',sa.Text(),server_default='',nullable=False),
            sa.Column('created_at',sa.DateTime(),server_default=sa.text('CURRENT_TIMESTAMP'),nullable=False),
            sa.Column('reviewed_at',sa.DateTime(),nullable=True))
        op.create_index('ix_governance_insights_campaign','governance_insights',['campaign_id'])
        op.create_index('ix_governance_insights_state','governance_insights',['state'])
    if op.get_bind().dialect.name=='postgresql':
        for name in ('governance_field_corrections','governance_insights'):
            op.execute('ALTER TABLE '+name+' ENABLE ROW LEVEL SECURITY')
            op.execute('REVOKE ALL ON TABLE '+name+' FROM PUBLIC, anon, authenticated')
            op.execute('REVOKE ALL ON SEQUENCE '+name+'_id_seq FROM PUBLIC, anon, authenticated')

def downgrade():
    # Intentionally non-destructive on shared BAWASLU Supabase.
    pass
