"""Persist evidence-grounded player intelligence and token usage.

Revision ID: 20261029_03
Revises: 20261029_02
"""
from alembic import op
import sqlalchemy as sa

revision='20261029_03'
down_revision='20261029_02'
branch_labels=None
depends_on=None

def upgrade():
    for name,default in (
        ('topic_labels_json','[]'),
        ('public_concern_signals_json','[]'),
        ('attention_assessment_json','{}'),
        ('player_summaries_json','[]')):
        op.add_column('evidence_assessments',sa.Column(name,sa.Text(),
            nullable=False,server_default=default))
    op.create_table('assessment_ai_usage',
        sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column('assessment_id',sa.Integer(),
                  sa.ForeignKey('evidence_assessments.id'),nullable=False),
        sa.Column('campaign_id',sa.Integer(),
                  sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
        sa.Column('provider_model',sa.String(length=100),nullable=False,server_default=''),
        sa.Column('request_kind',sa.String(length=40),nullable=False,server_default=''),
        sa.Column('input_tokens',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('output_tokens',sa.Integer(),nullable=False,server_default='0'),
        sa.Column('usage_reported',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('cost_usd',sa.String(length=64),nullable=False,server_default=''),
        sa.Column('cost_status',sa.String(length=64),nullable=False,server_default='NOT_REPORTED'),
        sa.Column('created_at',sa.DateTime(),nullable=True))
    op.create_index('ix_assessment_ai_usage_assessment_id',
        'assessment_ai_usage',['assessment_id'],unique=True)
    op.create_index('ix_assessment_ai_usage_campaign_id',
        'assessment_ai_usage',['campaign_id'])
    if op.get_bind().dialect.name=='postgresql':
        op.execute('ALTER TABLE assessment_ai_usage ENABLE ROW LEVEL SECURITY')
        op.execute('REVOKE ALL ON TABLE assessment_ai_usage FROM anon, authenticated')

def downgrade():
    op.drop_index('ix_assessment_ai_usage_campaign_id',table_name='assessment_ai_usage')
    op.drop_index('ix_assessment_ai_usage_assessment_id',table_name='assessment_ai_usage')
    op.drop_table('assessment_ai_usage')
    for name in ('player_summaries_json','attention_assessment_json',
                 'public_concern_signals_json','topic_labels_json'):
        op.drop_column('evidence_assessments',name)
